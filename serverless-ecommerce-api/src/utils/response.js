/**
 * Standard API response helper
 */

const corsHeaders = {
  'Content-Type': 'application/json',
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'Content-Type,Authorization,X-Amz-Date,X-Api-Key,X-Amz-Security-Token',
  'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
};

/**
 * Create a successful API response
 * @param {number} statusCode - HTTP status code
 * @param {Object} body - Response body
 * @param {Object} additionalHeaders - Additional headers
 * @returns {Object} API Gateway response object
 */
exports.createResponse = (statusCode, body, additionalHeaders = {}) => {
  return {
    statusCode,
    headers: {
      ...corsHeaders,
      ...additionalHeaders
    },
    body: JSON.stringify(body)
  };
};

/**
 * Create an error API response
 * @param {number} statusCode - HTTP status code
 * @param {string} message - Error message
 * @param {Object} details - Additional error details
 * @returns {Object} API Gateway response object
 */
exports.createErrorResponse = (statusCode, message, details = null) => {
  const body = {
    error: {
      code: statusCode,
      message,
      timestamp: new Date().toISOString()
    }
  };

  if (details) {
    body.error.details = details;
  }

  return {
    statusCode,
    headers: corsHeaders,
    body: JSON.stringify(body)
  };
};

/**
 * Common HTTP status codes
 */
exports.HttpStatus = {
  OK: 200,
  CREATED: 201,
  NO_CONTENT: 204,
  BAD_REQUEST: 400,
  UNAUTHORIZED: 401,
  FORBIDDEN: 403,
  NOT_FOUND: 404,
  CONFLICT: 409,
  UNPROCESSABLE_ENTITY: 422,
  INTERNAL_SERVER_ERROR: 500
};
