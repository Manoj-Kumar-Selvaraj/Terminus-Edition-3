package platform

func ApplicableRules(req Request) []RuleDefinition {
	var source []RuleDefinition
	switch req.Surface {
	case "package":
		source = PackageRules
	case "container":
		source = ContainerRules
	case "dependency":
		source = DependencyRules
	default:
		return nil
	}
	environment := req.Environment
	if environment != "prod" {
		environment = "nonprod"
	}
	selected := make([]RuleDefinition, 0, 16)
	for _, rule := range source {
		if rule.Manager == req.Manager && rule.Environment == environment {
			selected = append(selected, rule)
		}
	}
	return selected
}

func RuleByCode(req Request, code string) (RuleDefinition, bool) {
	for _, rule := range ApplicableRules(req) {
		if rule.Code == code {
			return rule, true
		}
	}
	return RuleDefinition{}, false
}

func FailClosedRules(req Request) []RuleDefinition {
	result := make([]RuleDefinition, 0, 16)
	for _, rule := range ApplicableRules(req) {
		if rule.FailClosed {
			result = append(result, rule)
		}
	}
	return result
}
