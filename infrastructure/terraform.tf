terraform{
    required_providers {
        # Provedor referente ao ambiente da aws
        aws = {
            source = "hashicorp/aws"
            version =  "~> 5.92"
        }
    }

    required_version = ">= 1.2"
}