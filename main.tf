terraform {
  required_providers {
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.25"
    }
  }
}

provider "kubernetes" {
  host                   = "https://127.0.0.1:49758"
  cluster_ca_certificate = file("~/.minikube/ca.crt")
  client_certificate     = file("~/.minikube/profiles/minikube/client.crt")
  client_key             = file("~/.minikube/profiles/minikube/client.key")
}

resource "kubernetes_pod" "example" {
  metadata {
    name = "example-pod"
    labels = {
      app = "example"
    }
  }

  spec {
    container {
      name  = "nginx"
      image = "nginx:1.25"
      port {
        container_port = 80
      }
    }
  }
}

