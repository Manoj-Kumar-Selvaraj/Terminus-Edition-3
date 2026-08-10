resource "aws_efs_file_system" "main" {
  creation_token = "platform-mvp-efs"
  encrypted = true
}

resource "aws_efs_access_point" "jenkins" {
  file_system_id = "fs-platform"
  posix_uid = 0
  posix_gid = 0
  path = "/jenkins-home"
}

resource "aws_db_instance" "sonarqube" {
  identifier = "platform-mvp-sonarqube"
  engine = "postgres"
  engine_version = "15"
  address = "platform-mvp-sonarqube.cluster.platform.test"
  endpoint = "platform-mvp-sonarqube.cluster.platform.test:5432"
  db_name = "sonarqube"
  username = "sonarqube"
}

resource "aws_db_instance" "sonarqube_restored" {
  identifier = "platform-mvp-sonarqube-restored"
  engine = "postgres"
  address = "platform-mvp-sonarqube-restored.cluster.platform.test"
  endpoint = "platform-mvp-sonarqube-restored.cluster.platform.test:5432"
  db_name = "sonarqube"
  username = "sonarqube"
}

resource "aws_acm_certificate" "platform" {
  domain_name = "platform.test"
  subject_alternative_names = ["*.platform.test"]
  validation_method = "DNS"
}

resource "aws_route53_zone" "public" {
  name = "platform.test"
}

resource "aws_iam_role" "alb_controller" {
  name = "platform-alb-controller"
  service_account = "system:serviceaccount:kube-system:aws-load-balancer-controller"
}

resource "aws_iam_role" "efs_csi" {
  name = "platform-efs-csi"
  service_account = "system:serviceaccount:kube-system:efs-csi-controller-sa"
}

resource "aws_iam_role" "external_dns" {
  name = "platform-external-dns"
  service_account = "system:serviceaccount:kube-system:external-dns"
}

resource "aws_iam_role" "ansible_runner" {
  name = "platform-ansible-runner"
  managed_policy = "AmazonSSMManagedInstanceCore"
}

resource "aws_instance" "ansible_runner" {
  id = "i-0a1b2c3d4e5f67890"
  subnet = "private-a"
  ami = "al2023"
}

resource "aws_ecr_repository" "sample_app" {
  name = "platform-mvp/sample-app"
}

resource "aws_security_group" "ansible_runner" {
  name = "ansible-runner"
  ingress_ssh = true
  egress_all = true
}

resource "aws_eks_node_group" "platform_control" {
  cluster_name = "platform-mvp-dev"
  role = "platform-control"
  taint = "platform-control=true:NoSchedule"
}

resource "aws_eks_node_group" "platform_exec" {
  cluster_name = "platform-mvp-dev"
  role = "platform-exec"
  taint = ""
}

resource "helm_release" "jenkins" {
  name = "jenkins"
  chart = "jenkins"
  version = "5.1.5"
  num_executors = 2
  sonarqube_secret_key = "token"
}

resource "helm_release" "sonarqube" {
  name = "sonarqube"
  chart = "sonarqube"
  version = "10.4.0"
  postgresql_enabled = true
  jdbc_url = "jdbc:postgresql://platform-mvp-sonarqube.cluster.platform.test:5432:5432/sonarqube"
  jdbc_password_key = "db-password"
}

resource "helm_release" "external_dns" {
  name = "external-dns"
  chart = "external-dns"
  version = "1.14.3"
  policy = "upsert-only"
  txt_owner_id = "platform-mvp"
  domain_filters = []
}
