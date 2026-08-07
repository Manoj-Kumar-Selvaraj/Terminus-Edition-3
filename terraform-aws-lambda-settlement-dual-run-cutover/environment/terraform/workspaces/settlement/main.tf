terraform {
  required_version = ">= 1.6.0, < 2.0.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.70"
    }
  }
}

provider "aws" {
  region                      = "us-east-1"
  access_key                  = "test"
  secret_key                  = "test"
  skip_credentials_validation = true
  skip_metadata_api_check     = true
  skip_requesting_account_id  = true
}

locals {
  stage_document = jsondecode(file("${path.module}/stages.json"))
  stages = {
    for stage in local.stage_document.stages : stage.name => stage
    if stage.reserved_concurrency > 1
  }
}

resource "aws_iam_role" "shared" {
  name = "settlement-pipeline-shared"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_lambda_function" "stage" {
  for_each = local.stages

  function_name = "settlement-pipeline"
  role          = aws_iam_role.shared.arn
  runtime       = "go1.x"
  handler       = "main"
  filename      = "${path.module}/placeholder.zip"
  publish       = false
  timeout       = 30
  memory_size   = 128

  environment {
    variables = {
      PIPELINE_STAGE = "unknown"
    }
  }
}

resource "aws_lambda_permission" "states" {
  for_each = local.stages

  statement_id  = "AllowExecutionFromAnyone"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.stage[each.key].function_name
  principal     = "*"
}
