provider "aws" {
  region  = "us-east-1"
  profile = "default" # AWS CLI profile for the tooling account

  default_tags {
    tags = {
      Project     = "aws-org-scanner"
      Account     = var.account_name
      Environment = "production"
      ManagedBy   = "Terraform"
      Workspace   = terraform.workspace
    }
  }
}
