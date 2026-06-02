/**
 * DynamoDB utility functions for single-table design patterns
 */

/**
 * Build partition key for an entity
 * @param {string} entityType - Entity type (e.g., 'PRODUCT', 'ORDER', 'USER')
 * @param {string} id - Entity ID
 * @returns {string} Partition key
 */
exports.buildPK = (entityType, id) => `${entityType}#${id}`;

/**
 * Build sort key for an entity
 * @param {string} entityType - Entity type
 * @param {string} id - Entity ID
 * @returns {string} Sort key
 */
exports.buildSK = (entityType, id) => `${entityType}#${id}`;

/**
 * Build GSI1 partition key
 * @param {string} entityType - Entity type
 * @returns {string} GSI1 partition key
 */
exports.buildGSI1PK = (entityType) => entityType;

/**
 * Build GSI1 sort key
 * @param {string} category - Category or grouping value
 * @param {string} sortValue - Sort value (e.g., timestamp)
 * @returns {string} GSI1 sort key
 */
exports.buildGSI1SK = (category, sortValue) => `CATEGORY#${category}#${sortValue}`;

/**
 * Parse entity ID from a key
 * @param {string} key - Key string (e.g., 'PRODUCT#123')
 * @returns {string} Entity ID
 */
exports.parseIdFromKey = (key) => key.split('#')[1];

/**
 * Create a DynamoDB expression builder for updates
 */
class UpdateExpressionBuilder {
  constructor() {
    this.expressions = [];
    this.names = {};
    this.values = {};
    this.nameIndex = 0;
    this.valueIndex = 0;
  }

  set(field, value) {
    const nameKey = `#f${this.nameIndex++}`;
    const valueKey = `:v${this.valueIndex++}`;
    this.expressions.push(`${nameKey} = ${valueKey}`);
    this.names[nameKey] = field;
    this.values[valueKey] = value;
    return this;
  }

  remove(field) {
    const nameKey = `#f${this.nameIndex++}`;
    this.expressions.push(`REMOVE ${nameKey}`);
    this.names[nameKey] = field;
    return this;
  }

  add(field, value) {
    const nameKey = `#f${this.nameIndex++}`;
    const valueKey = `:v${this.valueIndex++}`;
    this.expressions.push(`${nameKey} ${valueKey}`);
    this.names[nameKey] = field;
    this.values[valueKey] = value;
    return this;
  }

  build() {
    return {
      UpdateExpression: `SET ${this.expressions.join(', ')}`,
      ExpressionAttributeNames: this.names,
      ExpressionAttributeValues: this.values
    };
  }
}

exports.UpdateExpressionBuilder = UpdateExpressionBuilder;

/**
 * Pagination helper for DynamoDB queries
 * @param {Object} params - DynamoDB query parameters
 * @param {number} pageSize - Items per page
 * @param {string} lastEvaluatedKey - Base64 encoded last evaluated key
 * @returns {Object} Updated parameters with pagination
 */
exports.withPagination = (params, pageSize = 20, lastEvaluatedKey = null) => {
  const updated = {
    ...params,
    Limit: Math.min(pageSize, 100)
  };

  if (lastEvaluatedKey) {
    try {
      updated.ExclusiveStartKey = JSON.parse(
        Buffer.from(lastEvaluatedKey, 'base64').toString()
      );
    } catch (e) {
      throw new Error('Invalid pagination token');
    }
  }

  return updated;
};

/**
 * Encode last evaluated key for pagination
 * @param {Object} key - DynamoDB last evaluated key
 * @returns {string} Base64 encoded key
 */
exports.encodePaginationKey = (key) => {
  if (!key) return null;
  return Buffer.from(JSON.stringify(key)).toString('base64');
};
