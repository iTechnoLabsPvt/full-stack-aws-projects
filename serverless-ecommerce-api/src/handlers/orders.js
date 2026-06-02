const { Logger } = require('@aws-lambda-powertools/logger');
const { Tracer } = require('@aws-lambda-powertools/tracer');
const { DynamoDBDocumentClient, GetCommand, PutCommand, UpdateCommand } = require('@aws-sdk/lib-dynamodb');
const { DynamoDBClient } = require('@aws-sdk/client-dynamodb');
const { SQSClient, SendMessageCommand } = require('@aws-sdk/client-sqs');
const { v4: uuidv4 } = require('uuid');
const { createResponse, createErrorResponse } = require('../utils/response');
const { validateOrder } = require('../models/order');

const logger = new Logger({ serviceName: 'ecommerce-api' });
const tracer = new Tracer({ serviceName: 'ecommerce-api' });

const client = tracer.captureAWSv3Client(new DynamoDBClient({}));
const docClient = DynamoDBDocumentClient.from(client);
const sqsClient = tracer.captureAWSv3Client(new SQSClient({}));

const TABLE_NAME = process.env.TABLE_NAME;
const ORDER_QUEUE_URL = process.env.ORDER_QUEUE_URL;

/**
 * Create a new order
 */
exports.create = tracer.captureLambdaHandler(async (event) => {
  const userId = event.requestContext?.authorizer?.claims?.sub || 'anonymous';
  logger.info('Creating order', { userId });

  try {
    const body = JSON.parse(event.body);
    const { error, value } = validateOrder(body);

    if (error) {
      logger.warn('Order validation failed', { details: error.details });
      return createErrorResponse(400, 'Validation failed', error.details);
    }

    // Validate products exist and have sufficient stock
    const productChecks = await Promise.all(
      value.items.map(async (item) => {
        const result = await docClient.send(new GetCommand({
          TableName: TABLE_NAME,
          Key: {
            PK: `PRODUCT#${item.productId}`,
            SK: `PRODUCT#${item.productId}`
          }
        }));
        return { item, product: result.Item };
      })
    );

    const invalidItems = productChecks.filter(({ product }) => !product);
    if (invalidItems.length > 0) {
      return createErrorResponse(400, 'Invalid products in order', {
        invalidProductIds: invalidItems.map(({ item }) => item.productId)
      });
    }

    const outOfStock = productChecks.filter(
      ({ item, product }) => product.stock < item.quantity
    );
    if (outOfStock.length > 0) {
      return createErrorResponse(400, 'Insufficient stock', {
        outOfStockItems: outOfStock.map(({ item, product }) => ({
          productId: item.productId,
          requested: item.quantity,
          available: product.stock
        }))
      });
    }

    const orderId = uuidv4();
    const timestamp = new Date().toISOString();
    const totalAmount = productChecks.reduce(
      (sum, { item, product }) => sum + (product.price * item.quantity),
      0
    );

    const orderItem = {
      PK: `ORDER#${orderId}`,
      SK: `ORDER#${orderId}`,
      GSI1PK: `USER#${userId}`,
      GSI1SK: `ORDER#${timestamp}`,
      entityType: 'ORDER',
      id: orderId,
      userId,
      items: value.items.map(({ item, product }) => ({
        productId: item.productId,
        quantity: item.quantity,
        price: product.price,
        name: product.name
      })),
      totalAmount,
      status: 'PENDING',
      shippingAddress: value.shippingAddress,
      createdAt: timestamp,
      updatedAt: timestamp
    };

    // Save order to DynamoDB
    await docClient.send(new PutCommand({
      TableName: TABLE_NAME,
      Item: orderItem
    }));

    // Send to SQS for async processing
    await sqsClient.send(new SendMessageCommand({
      QueueUrl: ORDER_QUEUE_URL,
      MessageBody: JSON.stringify({ orderId, userId }),
      MessageAttributes: {
        orderId: { StringValue: orderId, DataType: 'String' },
        userId: { StringValue: userId, DataType: 'String' }
      }
    }));

    logger.info('Order created and queued for processing', { orderId, userId });
    return createResponse(201, {
      id: orderId,
      status: 'PENDING',
      totalAmount,
      items: orderItem.items,
      createdAt: timestamp
    });

  } catch (error) {
    logger.error('Error creating order', { userId, error: error.message });
    return createErrorResponse(500, 'Failed to create order');
  }
});

/**
 * Process orders from SQS queue
 */
exports.process = tracer.captureLambdaHandler(async (event) => {
  logger.info('Processing order batch', { recordCount: event.Records.length });

  const results = await Promise.allSettled(
    event.Records.map(async (record) => {
      const { orderId, userId } = JSON.parse(record.body);
      logger.info('Processing order', { orderId, userId });

      try {
        // Update order status to PROCESSING
        await docClient.send(new UpdateCommand({
          TableName: TABLE_NAME,
          Key: {
            PK: `ORDER#${orderId}`,
            SK: `ORDER#${orderId}`
          },
          UpdateExpression: 'SET #status = :status, updatedAt = :updatedAt',
          ExpressionAttributeNames: {
            '#status': 'status'
          },
          ExpressionAttributeValues: {
            ':status': 'PROCESSING',
            ':updatedAt': new Date().toISOString()
          }
        }));

        // Simulate payment processing
        await new Promise(resolve => setTimeout(resolve, 100));

        // Update order status to CONFIRMED
        await docClient.send(new UpdateCommand({
          TableName: TABLE_NAME,
          Key: {
            PK: `ORDER#${orderId}`,
            SK: `ORDER#${orderId}`
          },
          UpdateExpression: 'SET #status = :status, updatedAt = :updatedAt',
          ExpressionAttributeNames: {
            '#status': 'status'
          },
          ExpressionAttributeValues: {
            ':status': 'CONFIRMED',
            ':updatedAt': new Date().toISOString()
          }
        }));

        logger.info('Order processed successfully', { orderId });
        return { orderId, status: 'success' };

      } catch (error) {
        logger.error('Error processing order', { orderId, error: error.message });
        throw error;
      }
    })
  );

  const failures = results.filter(r => r.status === 'rejected');
  if (failures.length > 0) {
    logger.error('Some orders failed to process', { failureCount: failures.length });
    throw new Error(`${failures.length} orders failed to process`);
  }

  logger.info('All orders processed successfully');
  return { batchItemFailures: [] };
});
