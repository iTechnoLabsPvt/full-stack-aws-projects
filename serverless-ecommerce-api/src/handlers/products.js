const { Logger } = require('@aws-lambda-powertools/logger');
const { Tracer } = require('@aws-lambda-powertools/tracer');
const { DynamoDBDocumentClient, QueryCommand, GetCommand, PutCommand } = require('@aws-sdk/lib-dynamodb');
const { DynamoDBClient } = require('@aws-sdk/client-dynamodb');
const { v4: uuidv4 } = require('uuid');
const { createResponse, createErrorResponse } = require('../utils/response');
const { validateProduct } = require('../models/product');

const logger = new Logger({ serviceName: 'ecommerce-api' });
const tracer = new Tracer({ serviceName: 'ecommerce-api' });

const client = tracer.captureAWSv3Client(new DynamoDBClient({}));
const docClient = DynamoDBDocumentClient.from(client);
const TABLE_NAME = process.env.TABLE_NAME;

/**
 * Get all products with pagination support
 */
exports.getAll = tracer.captureLambdaHandler(async (event) => {
  logger.info('Fetching products', { queryParams: event.queryStringParameters });

  try {
    const limit = parseInt(event.queryStringParameters?.limit) || 20;
    const category = event.queryStringParameters?.category;

    const params = {
      TableName: TABLE_NAME,
      IndexName: 'GSI1',
      KeyConditionExpression: 'GSI1PK = :pk',
      ExpressionAttributeValues: {
        ':pk': 'PRODUCT'
      },
      Limit: Math.min(limit, 100)
    };

    if (category) {
      params.KeyConditionExpression += ' AND begins_with(GSI1SK, :cat)';
      params.ExpressionAttributeValues[':cat'] = `CATEGORY#${category}`;
    }

    if (event.queryStringParameters?.lastEvaluatedKey) {
      params.ExclusiveStartKey = JSON.parse(
        Buffer.from(event.queryStringParameters.lastEvaluatedKey, 'base64').toString()
      );
    }

    const result = await docClient.send(new QueryCommand(params));

    const products = result.Items.map(item => ({
      id: item.SK.replace('PRODUCT#', ''),
      name: item.name,
      description: item.description,
      price: item.price,
      category: item.category,
      stock: item.stock,
      images: item.images,
      createdAt: item.createdAt
    }));

    const response = {
      products,
      count: products.length,
      totalCount: result.Count
    };

    if (result.LastEvaluatedKey) {
      response.nextPageToken = Buffer.from(
        JSON.stringify(result.LastEvaluatedKey)
      ).toString('base64');
    }

    logger.info('Products fetched successfully', { count: products.length });
    return createResponse(200, response);

  } catch (error) {
    logger.error('Error fetching products', { error: error.message });
    return createErrorResponse(500, 'Failed to fetch products');
  }
});

/**
 * Get product by ID
 */
exports.getById = tracer.captureLambdaHandler(async (event) => {
  const productId = event.pathParameters?.id;
  logger.info('Fetching product', { productId });

  try {
    const result = await docClient.send(new GetCommand({
      TableName: TABLE_NAME,
      Key: {
        PK: `PRODUCT#${productId}`,
        SK: `PRODUCT#${productId}`
      }
    }));

    if (!result.Item) {
      return createErrorResponse(404, 'Product not found');
    }

    const product = {
      id: productId,
      name: result.Item.name,
      description: result.Item.description,
      price: result.Item.price,
      category: result.Item.category,
      stock: result.Item.stock,
      images: result.Item.images,
      createdAt: result.Item.createdAt
    };

    logger.info('Product fetched successfully', { productId });
    return createResponse(200, product);

  } catch (error) {
    logger.error('Error fetching product', { productId, error: error.message });
    return createErrorResponse(500, 'Failed to fetch product');
  }
});

/**
 * Create a new product (Admin only)
 */
exports.create = tracer.captureLambdaHandler(async (event) => {
  logger.info('Creating product');

  try {
    const body = JSON.parse(event.body);
    const { error, value } = validateProduct(body);

    if (error) {
      logger.warn('Validation failed', { details: error.details });
      return createErrorResponse(400, 'Validation failed', error.details);
    }

    const productId = uuidv4();
    const timestamp = new Date().toISOString();

    const item = {
      PK: `PRODUCT#${productId}`,
      SK: `PRODUCT#${productId}`,
      GSI1PK: 'PRODUCT',
      GSI1SK: `CATEGORY#${value.category}#${timestamp}`,
      entityType: 'PRODUCT',
      id: productId,
      ...value,
      createdAt: timestamp,
      updatedAt: timestamp
    };

    await docClient.send(new PutCommand({
      TableName: TABLE_NAME,
      Item: item,
      ConditionExpression: 'attribute_not_exists(PK)'
    }));

    logger.info('Product created successfully', { productId });
    return createResponse(201, {
      id: productId,
      ...value,
      createdAt: timestamp
    });

  } catch (error) {
    if (error.name === 'ConditionalCheckFailedException') {
      return createErrorResponse(409, 'Product already exists');
    }
    logger.error('Error creating product', { error: error.message });
    return createErrorResponse(500, 'Failed to create product');
  }
});
