const Joi = require('joi');

const orderItemSchema = Joi.object({
  productId: Joi.string().uuid().required()
    .description('Product ID'),

  quantity: Joi.number().integer().min(1).max(100).required()
    .description('Quantity to order')
});

const addressSchema = Joi.object({
  street: Joi.string().min(5).max(200).required(),
  city: Joi.string().min(2).max(100).required(),
  state: Joi.string().min(2).max(100).required(),
  zipCode: Joi.string().pattern(/^\d{5}(-\d{4})?$/).required(),
  country: Joi.string().length(2).uppercase().default('US')
});

const orderSchema = Joi.object({
  items: Joi.array().items(orderItemSchema).min(1).max(50).required()
    .description('Order items'),

  shippingAddress: addressSchema.required()
    .description('Shipping address'),

  billingAddress: addressSchema
    .description('Billing address (defaults to shipping)'),

  notes: Joi.string().max(500).allow('').default('')
    .description('Order notes'),

  couponCode: Joi.string().alphanum().max(20).uppercase()
    .description('Discount coupon code')
});

/**
 * Validate order data
 * @param {Object} data - Order data to validate
 * @returns {Object} - { error, value }
 */
exports.validateOrder = (data) => {
  return orderSchema.validate(data, {
    abortEarly: false,
    stripUnknown: true
  });
};

/**
 * Order status enum
 */
exports.OrderStatus = {
  PENDING: 'PENDING',
  PROCESSING: 'PROCESSING',
  CONFIRMED: 'CONFIRMED',
  SHIPPED: 'SHIPPED',
  DELIVERED: 'DELIVERED',
  CANCELLED: 'CANCELLED',
  REFUNDED: 'REFUNDED'
};

/**
 * Check if status transition is valid
 */
exports.isValidStatusTransition = (currentStatus, newStatus) => {
  const transitions = {
    PENDING: ['PROCESSING', 'CANCELLED'],
    PROCESSING: ['CONFIRMED', 'CANCELLED'],
    CONFIRMED: ['SHIPPED', 'CANCELLED'],
    SHIPPED: ['DELIVERED'],
    DELIVERED: ['REFUNDED'],
    CANCELLED: [],
    REFUNDED: []
  };

  return transitions[currentStatus]?.includes(newStatus) || false;
};
