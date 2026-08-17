package observe

import (
	"bufio"
	"fmt"
	"os"
	"os/user"
	"sort"
	"strconv"
	"strings"
)

type UserState struct {
	Exists bool
	Name   string
	UID    int64
	GID    int64
	Group  string
	Groups []string
	Home   string
	Shell  string
}

type GroupState struct {
	Exists  bool
	Name    string
	GID     int64
	Members []string
}

func InspectUser(name string) (UserState, error) {
	u, err := user.Lookup(name)
	if err != nil {
		if _, ok := err.(user.UnknownUserError); ok {
			return UserState{Name: name}, nil
		}
		return UserState{Name: name}, fmt.Errorf("lookup user %s: %w", name, err)
	}
	uid, _ := strconv.ParseInt(u.Uid, 10, 64)
	gid, _ := strconv.ParseInt(u.Gid, 10, 64)
	state := UserState{Exists: true, Name: name, UID: uid, GID: gid, Home: u.HomeDir}
	if g, err := user.LookupGroupId(u.Gid); err == nil {
		state.Group = g.Name
	}
	state.Shell = shellForUser(name)
	state.Groups = supplementaryGroups(u)
	return state, nil
}

func InspectGroup(name string) (GroupState, error) {
	g, err := user.LookupGroup(name)
	if err != nil {
		if _, ok := err.(user.UnknownGroupError); ok {
			return GroupState{Name: name}, nil
		}
		return GroupState{Name: name}, fmt.Errorf("lookup group %s: %w", name, err)
	}
	gid, _ := strconv.ParseInt(g.Gid, 10, 64)
	return GroupState{Exists: true, Name: name, GID: gid, Members: membersForGroup(name)}, nil
}

func shellForUser(name string) string {
	f, err := os.Open("/etc/passwd")
	if err != nil {
		return ""
	}
	defer f.Close()
	scanner := bufio.NewScanner(f)
	prefix := name + ":"
	for scanner.Scan() {
		line := scanner.Text()
		if !strings.HasPrefix(line, prefix) {
			continue
		}
		parts := strings.Split(line, ":")
		if len(parts) >= 7 {
			return parts[6]
		}
	}
	return ""
}

func supplementaryGroups(u *user.User) []string {
	ids, err := u.GroupIds()
	if err != nil {
		return nil
	}
	groups := make([]string, 0, len(ids))
	for _, id := range ids {
		if id == u.Gid {
			continue
		}
		g, err := user.LookupGroupId(id)
		if err == nil {
			groups = append(groups, g.Name)
		}
	}
	sort.Strings(groups)
	return groups
}

func membersForGroup(name string) []string {
	f, err := os.Open("/etc/group")
	if err != nil {
		return nil
	}
	defer f.Close()
	scanner := bufio.NewScanner(f)
	prefix := name + ":"
	for scanner.Scan() {
		line := scanner.Text()
		if !strings.HasPrefix(line, prefix) {
			continue
		}
		parts := strings.Split(line, ":")
		if len(parts) < 4 || parts[3] == "" {
			return nil
		}
		members := strings.Split(parts[3], ",")
		sort.Strings(members)
		return members
	}
	return nil
}
