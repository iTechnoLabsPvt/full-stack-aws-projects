# Full-Stack Task Manager

A modern, scalable task management application built with React, Node.js/Express, PostgreSQL, and deployed on AWS ECS Fargate using Terraform. Features real-time collaboration, role-based access control, and comprehensive CI/CD.

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   React     │────▶│  CloudFront  │────▶│     S3      │
│   (SPA)     │     │   + Route53  │     │  (Static)   │
└──────┬──────┘     └──────────────┘     └─────────────┘
       │
       │ HTTPS
       ▼
┌──────────────┐     ┌──────────────┐     ┌─────────────┐
│      ALB     │────▶│  ECS Fargate │────▶│  PostgreSQL │
│  (HTTPS/TLS) │     │   (Node.js)  │     │   (RDS)     │
└──────────────┘     └──────────────┘     └─────────────┘
                            │
                            ▼
                     ┌──────────────┐
                     │ ElastiCache  │
                     │   (Redis)    │
                     └──────────────┘
```

## Tech Stack

### Frontend
- **React 18** with TypeScript
- **Vite** for build tooling
- **Tailwind CSS** for styling
- **React Query** for server state management
- **Zustand** for client state
- **React Router v6** for routing

### Backend
- **Node.js 20** with Express
- **TypeScript**
- **Prisma ORM** with PostgreSQL
- **Redis** for caching & sessions
- **JWT** authentication with refresh tokens
- **Winston** structured logging
- **Jest + Supertest** for testing

### Infrastructure
- **AWS ECS Fargate** - Container orchestration
- **Amazon RDS PostgreSQL** - Managed database
- **Amazon ElastiCache Redis** - Caching layer
- **Application Load Balancer** - Traffic distribution
- **AWS VPC** - Network isolation
- **Terraform** - Infrastructure as Code
- **Docker** - Containerization
- **GitHub Actions** - CI/CD pipeline

## Features

- User authentication (JWT + refresh tokens)
- Role-based access control (Admin, Manager, Member)
- Task CRUD with real-time updates via WebSockets
- Project & team management
- Task assignments & deadlines
- Activity feed & notifications
- File attachments (S3)
- Search & filtering
- Dark mode support
- Responsive design

## Getting Started

### Prerequisites

- Docker & Docker Compose
- Node.js 20+
- Terraform 1.6+
- AWS CLI configured

### Local Development

```bash
# Start infrastructure
docker-compose up -d

# Backend
cd backend
npm install
npm run db:migrate
npm run db:seed
npm run dev

# Frontend
cd frontend
npm install
npm run dev
```

### Deploy to AWS

```bash
cd infrastructure/environments/dev
terraform init
terraform plan
terraform apply
```

## API Documentation

API documentation is available at `/api/docs` when running the backend (Swagger UI).

## Project Structure

```
.
├── backend/           # Express API
├── frontend/          # React SPA
├── infrastructure/    # Terraform modules
└── docker-compose.yml # Local development
```

## License

MIT
