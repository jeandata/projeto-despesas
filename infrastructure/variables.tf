variable "aws_region" {
  description = "Região principal da AWS"
  default     = "us-east-2"
}

variable "project_tags" {
  description = "Tags padrão para todos os recursos"
  type        = map(string)
  default     = {
    Jornada   = "Dados"
    Gerenciado = "Terraform"
  }
}