const { mockClient } = require('aws-sdk-client-mock');
const { DynamoDBDocumentClient, QueryCommand, GetCommand, PutCommand } = require('@aws-sdk/lib-dynamodb');
const { products } = require('../src/handlers/products');

const ddbMock = mockClient(DynamoDBDocumentClient);

describe('Products Handler', () => {
  beforeEach(() => {
    ddbMock.reset();
    process.env.TABLE_NAME = 'test-table';
  });

  afterEach(() => {
    ddbMock.restore();
  });

  describe('getAll', () => {
    it('should return paginated products', async () => {
      const mockProducts = [
        {
          PK: 'PRODUCT#1',
          SK: 'PRODUCT#1',
          GSI1PK: 'PRODUCT',
          GSI1SK: 'CATEGORY#electronics#2024-01-01',
          name: 'Laptop',
          description: 'High-performance laptop',
          price: 999.99,
          category: 'electronics',
          stock: 10,
          images: [],
          createdAt: '2024-01-01T00:00:00Z'
        }
      ];

      ddbMock.on(QueryCommand).resolves({
        Items: mockProducts,
        Count: 1
      });

      const event = {
        queryStringParameters: { limit: '10' }
      };

      const result = await products.getAll(event);
      const body = JSON.parse(result.body);

      expect(result.statusCode).toBe(200);
      expect(body.products).toHaveLength(1);
      expect(body.products[0].name).toBe('Laptop');
      expect(body.count).toBe(1);
    });

    it('should filter products by category', async () => {
      ddbMock.on(QueryCommand).resolves({
        Items: [],
        Count: 0
      });

      const event = {
        queryStringParameters: { category: 'electronics', limit: '10' }
      };

      const result = await products.getAll(event);
      const body = JSON.parse(result.body);

      expect(result.statusCode).toBe(200);
      expect(body.products).toHaveLength(0);

      const call = ddbMock.commandCalls(QueryCommand)[0];
      expect(call.args[0].input.KeyConditionExpression).toContain('begins_with');
    });

    it('should handle pagination tokens', async () => {
      const lastKey = Buffer.from(JSON.stringify({ PK: 'PRODUCT#1', SK: 'PRODUCT#1' })).toString('base64');

      ddbMock.on(QueryCommand).resolves({
        Items: [],
        Count: 0
      });

      const event = {
        queryStringParameters: { lastEvaluatedKey: lastKey }
      };

      await products.getAll(event);

      const call = ddbMock.commandCalls(QueryCommand)[0];
      expect(call.args[0].input.ExclusiveStartKey).toEqual({
        PK: 'PRODUCT#1',
        SK: 'PRODUCT#1'
      });
    });
  });

  describe('getById', () => {
    it('should return a product by ID', async () => {
      const mockProduct = {
        PK: 'PRODUCT#123',
        SK: 'PRODUCT#123',
        name: 'Test Product',
        description: 'A test product',
        price: 29.99,
        category: 'books',
        stock: 50,
        images: ['https://example.com/image.jpg'],
        createdAt: '2024-01-01T00:00:00Z'
      };

      ddbMock.on(GetCommand).resolves({ Item: mockProduct });

      const event = {
        pathParameters: { id: '123' }
      };

      const result = await products.getById(event);
      const body = JSON.parse(result.body);

      expect(result.statusCode).toBe(200);
      expect(body.id).toBe('123');
      expect(body.name).toBe('Test Product');
    });

    it('should return 404 for non-existent product', async () => {
      ddbMock.on(GetCommand).resolves({ Item: null });

      const event = {
        pathParameters: { id: 'nonexistent' }
      };

      const result = await products.getById(event);
      const body = JSON.parse(result.body);

      expect(result.statusCode).toBe(404);
      expect(body.error.message).toBe('Product not found');
    });
  });

  describe('create', () => {
    it('should create a new product', async () => {
      ddbMock.on(PutCommand).resolves({});

      const event = {
        body: JSON.stringify({
          name: 'New Product',
          description: 'A brand new product for testing',
          price: 49.99,
          category: 'electronics',
          stock: 100,
          images: []
        })
      };

      const result = await products.create(event);
      const body = JSON.parse(result.body);

      expect(result.statusCode).toBe(201);
      expect(body.id).toBeDefined();
      expect(body.name).toBe('New Product');
      expect(body.price).toBe(49.99);
    });

    it('should return 400 for invalid product data', async () => {
      const event = {
        body: JSON.stringify({
          name: 'A',
          description: 'Short',
          price: -10,
          category: 'invalid',
          stock: -5
        })
      };

      const result = await products.create(event);
      const body = JSON.parse(result.body);

      expect(result.statusCode).toBe(400);
      expect(body.error.message).toBe('Validation failed');
      expect(body.error.details).toBeDefined();
    });

    it('should return 409 for duplicate product', async () => {
      const error = new Error('Conditional check failed');
      error.name = 'ConditionalCheckFailedException';
      ddbMock.on(PutCommand).rejects(error);

      const event = {
        body: JSON.stringify({
          name: 'Duplicate Product',
          description: 'This is a duplicate product entry for testing purposes',
          price: 29.99,
          category: 'books',
          stock: 10,
          images: []
        })
      };

      const result = await products.create(event);
      const body = JSON.parse(result.body);

      expect(result.statusCode).toBe(409);
      expect(body.error.message).toBe('Product already exists');
    });
  });
});
