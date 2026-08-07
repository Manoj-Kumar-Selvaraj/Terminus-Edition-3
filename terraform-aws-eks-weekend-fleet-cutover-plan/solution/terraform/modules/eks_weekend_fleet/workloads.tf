resource "kubernetes_daemon_set_v1" "artifactory_credential_helper" {
  metadata {
    name      = var.artifactory.daemonset_name
    namespace = var.artifactory.namespace

    labels = {
      "app.kubernetes.io/name"      = var.artifactory.daemonset_name
      "app.kubernetes.io/component" = "registry-credentials"
    }
  }

  spec {
    selector {
      match_labels = {
        "app.kubernetes.io/name" = var.artifactory.daemonset_name
      }
    }

    template {
      metadata {
        labels = {
          "app.kubernetes.io/name" = var.artifactory.daemonset_name
        }
      }

      spec {
        image_pull_secrets {
          name = var.artifactory.pull_secret_name
        }

        container {
          name  = "credential-helper"
          image = var.artifactory.helper_image

          env {
            name  = "ARTIFACTORY_REGISTRY_URL"
            value = var.artifactory.registry_host
          }

          env {
            name  = "ARTIFACTORY_REFRESH_INTERVAL_SECONDS"
            value = tostring(var.artifactory.refresh_interval_seconds)
          }

          env {
            name = "ARTIFACTORY_USERNAME"

            value_from {
              secret_key_ref {
                name = var.artifactory.pull_secret_name
                key  = var.artifactory.username_secret_key
              }
            }
          }

          env {
            name = "ARTIFACTORY_PASSWORD"

            value_from {
              secret_key_ref {
                name = var.artifactory.pull_secret_name
                key  = var.artifactory.password_secret_key
              }
            }
          }
        }
      }
    }
  }
}

resource "kubernetes_ingress_class_v1" "alb" {
  metadata {
    name = var.ingress.ingress_class_name
  }

  spec {
    controller = var.ingress.controller
  }
}

resource "kubernetes_ingress_v1" "placeholder" {
  metadata {
    name      = var.ingress.placeholder_name
    namespace = var.ingress.namespace

    annotations = {
      "alb.ingress.kubernetes.io/scheme"      = var.ingress.scheme
      "alb.ingress.kubernetes.io/target-type" = var.ingress.target_type
    }
  }

  spec {
    ingress_class_name = var.ingress.ingress_class_name

    rule {
      host = var.ingress.placeholder_host

      http {
        path {
          path      = "/"
          path_type = "Prefix"

          backend {
            service {
              name = var.ingress.service_name

              port {
                number = var.ingress.service_port
              }
            }
          }
        }
      }
    }
  }

  depends_on = [kubernetes_ingress_class_v1.alb]
}
