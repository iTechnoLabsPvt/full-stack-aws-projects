# Serverless E-commerce API

A production-ready serverless e-commerce backend built with AWS SAM, Lambda, API Gateway, and DynamoDB. Features include product catalog management, order processing, user authentication, and payment webhook handling.

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   Client    │────▶│ API Gateway  │────▶│   Lambda    │
└─────────────┘     └──────────────┘     └──────┬──────┘
                                                │
                                       ┌────────▼────────┐
                                       │    DynamoDB     │
                                       │  (Single-Table) │
                                       └─────────────────┘
```

## Tech Stack

- **AWS SAM** - Infrastructure as Code
- **AWS Lambda** - Serverless compute (Node.js 20.x)
- **Amazon API Gateway** - RESTful API endpoints
- **Amazon DynamoDB** - Single-table design for data persistence
- **AWS Cognito** - User authentication & authorization
- **Amazon SQS** - Async order processing
- **AWS X-Ray** - Distributed tracing

## Features

- Product CRUD operations with pagination & filtering
- Order lifecycle management (created → paid → shipped → delivered)
- JWT-based authentication via Cognito User Pools
- Event-driven architecture with SQS for order processing
- Comprehensive input validation & error handling
- Structured logging with correlation IDs
- Unit & integration tests with 85%+ coverage

## Getting Started

### Prerequisites

- AWS CLI configured
- SAM CLI installed
- Node.js 20.x

### Deploy

```bash
# Install dependencies
npm install

# Build the application
sam build

# Deploy to AWS
sam deploy --guided

# Run tests
npm test
```

## API Endpoints

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | /products | List products | No |
| GET | /products/{id} | Get product | No |
| POST | /products | Create product | Admin |
| POST | /orders | Create order | Yes |
| GET | /orders/{id} | Get order | Yes |
| POST | /webhooks/stripe | Stripe webhook | No |

## Project Structure

```
.
├── src/
│   ├── handlers/        # Lambda function handlers
│   ├── models/          # Data models & validation
│   └── utils/           # Shared utilities
├── tests/               # Unit & integration tests
├── template.yaml        # SAM infrastructure template
└── samconfig.toml       # SAM deployment config
```

## License

MIT
