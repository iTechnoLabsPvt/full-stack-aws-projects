const Joi = require('joi');

const productSchema = Joi.object({
  name: Joi.string().min(2).max(200).required()
    .description('Product name'),

  description: Joi.string().min(10).max(2000).required()
    .description('Product description'),

  price: Joi.number().positive().precision(2).required()
    .description('Product price in USD'),

  category: Joi.string().valid(
    'electronics', 'clothing', 'home', 'sports', 'books', 'food'
  ).required().description('Product category'),

  stock: Joi.number().integer().min(0).required()
    .description('Available stock quantity'),

  images: Joi.array().items(
    Joi.string().uri().max(500)
  ).max(10).default([]).description('Product image URLs'),

  tags: Joi.array().items(
    Joi.string().max(50)
  ).max(20).default([]).description('Product tags'),

  attributes: Joi.object().pattern(
    Joi.string().max(50),
    Joi.alternatives().try(Joi.string(), Joi.number())
  ).default({}).description('Additional product attributes')
});

/**
 * Validate product data
 * @param {Object} data - Product data to validate
 * @returns {Object} - { error, value }
 */
exports.validateProduct = (data) => {
  return productSchema.validate(data, {
    abortEarly: false,
    stripUnknown: true
  });
};

/**
 * Product entity class for domain logic
 */
class Product {
  constructor(data) {
    const { error, value } = productSchema.validate(data);
    if (error) {
      throw new Error(`Invalid product data: ${error.message}`);
    }
    Object.assign(this, value);
  }

  isInStock(quantity = 1) {
    return this.stock >= quantity;
  }

  reduceStock(quantity) {
    if (!this.isInStock(quantity)) {
      throw new Error('Insufficient stock');
    }
    this.stock -= quantity;
    return this;
  }

  toDynamoDBItem(productId) {
    const timestamp = new Date().toISOString();
    return {
      PK: `PRODUCT#${productId}`,
      SK: `PRODUCT#${productId}`,
      GSI1PK: 'PRODUCT',
      GSI1SK: `CATEGORY#${this.category}#${timestamp}`,
      entityType: 'PRODUCT',
      id: productId,
      ...this,
      createdAt: timestamp,
      updatedAt: timestamp
    };
  }
}

exports.Product = Product;
