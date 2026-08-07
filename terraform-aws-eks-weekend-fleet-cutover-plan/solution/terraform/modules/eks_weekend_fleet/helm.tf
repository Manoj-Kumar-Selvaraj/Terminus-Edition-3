resource "helm_release" "this" {
  for_each = var.helm_releases

  name      = each.key
  namespace = each.value.namespace
  chart     = "${var.chart_root}/${each.value.chart_dir}"
  version   = each.value.chart_version

  create_namespace  = false
  dependency_update = false
  atomic            = false

  dynamic "set" {
    for_each = merge(
      each.value.set_values,
      lookup(local.helm_controller_values, each.key, {}),
      {
        "serviceAccount.create" = "true"
      },
      each.value.irsa_role == "" ? {} : {
        "serviceAccount.name"                                       = var.irsa_roles[each.value.irsa_role].service_account
        "serviceAccount.annotations.eks\\.amazonaws\\.com/role-arn" = local.irsa_role_arns[each.value.irsa_role]
      },
    )

    content {
      name  = set.key
      value = set.value
    }
  }

  depends_on = [
    aws_eks_addon.this,
    aws_iam_role_policy.irsa,
  ]
}
