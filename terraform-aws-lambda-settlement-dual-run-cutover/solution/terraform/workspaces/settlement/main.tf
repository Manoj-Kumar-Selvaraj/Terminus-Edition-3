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
  }
  deployment = jsondecode(file("${path.module}/deployment.json"))
}

resource "aws_iam_role" "stage" {
  for_each = local.stages
  name     = "${each.value.function_name}-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "stage" {
  for_each = local.stages
  name     = "${each.value.function_name}-policy"
  role     = aws_iam_role.stage[each.key].id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = each.value.permissions
      Resource = ["*"]
    }]
  })
}

resource "aws_lambda_function" "stage" {
  for_each = local.stages

  function_name                  = each.value.function_name
  role                           = aws_iam_role.stage[each.key].arn
  runtime                        = "provided.al2023"
  handler                        = "bootstrap"
  architectures                  = ["arm64"]
  filename                       = "${path.module}/placeholder.zip"
  source_code_hash               = each.value.package_hash
  publish                        = true
  timeout                        = each.value.timeout_seconds
  memory_size                    = each.value.memory_mb
  reserved_concurrent_executions = each.value.reserved_concurrency

  environment {
    variables = {
      PIPELINE_STAGE      = each.key
      PIPELINE_GENERATION = tostring(local.deployment.generation)
    }
  }
}

resource "aws_lambda_permission" "states" {
  for_each = local.stages

  statement_id  = "AllowExecutionFromStates"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.stage[each.key].function_name
  principal     = "states.amazonaws.com"
  qualifier     = aws_lambda_alias.live[each.key].name
}

resource "aws_lambda_alias" "live" {
  for_each = local.stages

  name             = "live"
  function_name    = aws_lambda_function.stage[each.key].function_name
  function_version = aws_lambda_function.stage[each.key].version
}
