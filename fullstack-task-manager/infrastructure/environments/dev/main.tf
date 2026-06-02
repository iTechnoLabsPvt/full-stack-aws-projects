terraform {
  required_version = ">= 1.6.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket         = "taskmanager-terraform-state"
    key            = "dev/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "taskmanager-terraform-locks"
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = var.project_name
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}

# VPC Module
module "vpc" {
  source = "../../modules/vpc"

  project_name = var.project_name
  environment  = var.environment
  vpc_cidr     = "10.0.0.0/16"
  az_count     = 2
}

# ALB Module
module "alb" {
  source = "../../modules/alb"

  project_name      = var.project_name
  environment       = var.environment
  vpc_id            = module.vpc.vpc_id
  public_subnet_ids = module.vpc.public_subnet_ids
  certificate_arn   = var.certificate_arn
}

# RDS Module
module "rds" {
  source = "../../modules/rds"

  project_name               = var.project_name
  environment                = var.environment
  vpc_id                     = module.vpc.vpc_id
  private_subnet_ids         = module.vpc.private_subnet_ids
  allowed_security_group_ids = [module.ecs.security_group_id]
  database_name              = var.database_name
  master_username            = var.db_username
  master_password            = var.db_password
  instance_class             = "db.t3.micro"
}

# ECS Module
module "ecs" {
  source = "../../modules/ecs"

  project_name          = var.project_name
  environment           = var.environment
  aws_region            = var.aws_region
  vpc_id                = module.vpc.vpc_id
  private_subnet_ids    = module.vpc.private_subnet_ids
  container_image       = var.container_image
  target_group_arn      = module.alb.target_group_arn
  alb_security_group_id = module.alb.security_group_id

  environment_variables = {
    NODE_ENV        = var.environment
    DATABASE_URL    = "postgresql://${var.db_username}:${var.db_password}@${module.rds.db_endpoint}/${var.database_name}"
    REDIS_URL       = "redis://${module.rds.redis_endpoint}:${module.rds.redis_port}"
    JWT_SECRET      = var.jwt_secret
    JWT_REFRESH_SECRET = var.jwt_refresh_secret
    FRONTEND_URL    = "https://${var.domain_name}"
    LOG_LEVEL       = "info"
  }

  secrets = {
    # Add Secrets Manager ARNs here if needed
  }
}

# Route53 Record
resource "aws_route53_record" "app" {
  zone_id = var.route53_zone_id
  name    = var.domain_name
  type    = "A"

  alias {
    name                   = module.alb.alb_dns_name
    zone_id                = module.alb.alb_zone_id
    evaluate_target_health = true
  }
}
