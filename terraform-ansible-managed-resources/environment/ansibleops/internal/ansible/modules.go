package ansible

import "strings"

func FileTask(name, path, state, mode, owner, group string, force bool) Task {
	args := map[string]any{
		"path":  path,
		"state": state,
	}
	put(args, "mode", mode)
	put(args, "owner", owner)
	put(args, "group", group)
	if force {
		args["force"] = true
	}
	return Task{Name: name, Module: "ansible.builtin.file", Args: args, Become: true}
}

func CopyTask(name, source, destination, mode, owner, group string) Task {
	args := map[string]any{
		"src":  source,
		"dest": destination,
	}
	put(args, "mode", mode)
	put(args, "owner", owner)
	put(args, "group", group)
	return Task{Name: name, Module: "ansible.builtin.copy", Args: args, Become: true}
}

func TemplateTask(name, source, destination, mode, owner, group string, variables map[string]string) Task {
	args := map[string]any{
		"src":  source,
		"dest": destination,
	}
	put(args, "mode", mode)
	put(args, "owner", owner)
	put(args, "group", group)
	return Task{Name: name, Module: "ansible.builtin.template", Args: args, Vars: variables, Become: true}
}

func LineTask(name, path, line, regexp string, create bool, state string) Task {
	args := map[string]any{
		"path":   path,
		"line":   line,
		"create": create,
		"state":  state,
	}
	put(args, "regexp", regexp)
	return Task{Name: name, Module: "ansible.builtin.lineinfile", Args: args, Become: true}
}

func BlockTask(name, path, block, marker string, create bool, state string) Task {
	args := map[string]any{
		"path":   path,
		"block":  block,
		"create": create,
		"state":  state,
	}
	put(args, "marker", marker)
	return Task{Name: name, Module: "ansible.builtin.blockinfile", Args: args, Become: true}
}

func UserTask(name, userName, state string, uid int64, primaryGroup string, groups []string, shell, home string, createHome, remove bool) Task {
	args := map[string]any{
		"name":        userName,
		"state":       state,
		"create_home": createHome,
	}
	if uid > 0 {
		args["uid"] = uid
	}
	put(args, "group", primaryGroup)
	if len(groups) > 0 {
		args["groups"] = strings.Join(groups, ",")
		args["append"] = false
	}
	put(args, "shell", shell)
	put(args, "home", home)
	if remove {
		args["remove"] = true
	}
	return Task{Name: name, Module: "ansible.builtin.user", Args: args, Become: true}
}

func GroupTask(name, groupName, state string, gid int64, system bool) Task {
	args := map[string]any{
		"name":   groupName,
		"state":  state,
		"system": system,
	}
	if gid > 0 {
		args["gid"] = gid
	}
	return Task{Name: name, Module: "ansible.builtin.group", Args: args, Become: true}
}

func CronTask(name, entryName, user, minute, hour, day, month, weekday, job, state string, disabled bool) Task {
	args := map[string]any{
		"name":     entryName,
		"user":     user,
		"minute":   minute,
		"hour":     hour,
		"day":      day,
		"month":    month,
		"weekday":  weekday,
		"job":      job,
		"state":    state,
		"disabled": disabled,
	}
	return Task{Name: name, Module: "ansible.builtin.cron", Args: args, Become: true}
}

func put(args map[string]any, key, value string) {
	if strings.TrimSpace(value) != "" {
		args[key] = value
	}
}
