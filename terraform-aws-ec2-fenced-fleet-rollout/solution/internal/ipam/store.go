package ipam

import (
	"database/sql"
	"fmt"
	"os"
	"sort"
	"sync"

	"fleetrollout/internal/types"

	_ "modernc.org/sqlite"
)

type Subnet struct {
	ID        string
	AccountID string
	AZ        string
	Tier      string
	CIDR      string
}

type Image struct {
	AMIID     string
	Owner     string
	Arch      string
	State     string
	Deprecated bool
}

type Catalog struct {
	mu      sync.Mutex
	db      *sql.DB
	subnets map[string]Subnet
	images  map[string]Image
}

func Open(path string) (*Catalog, error) {
	if path == "" {
		path = os.Getenv("FLEET_IPAM")
	}
	if path == "" {
		path = types.IPAMPath
	}
	db, err := sql.Open("sqlite", path)
	if err != nil {
		return nil, fmt.Errorf("open ipam catalog: %w", err)
	}
	if err := db.Ping(); err != nil {
		_ = db.Close()
		return nil, fmt.Errorf("ping ipam catalog: %w", err)
	}
	cat := &Catalog{db: db, subnets: map[string]Subnet{}, images: map[string]Image{}}
	if err := cat.load(); err != nil {
		_ = db.Close()
		return nil, err
	}
	return cat, nil
}

func (c *Catalog) Close() error {
	c.mu.Lock()
	defer c.mu.Unlock()
	if c.db == nil {
		return nil
	}
	return c.db.Close()
}

func (c *Catalog) load() error {
	rows, err := c.db.Query(`SELECT id, account_id, az, tier, cidr FROM subnets`)
	if err != nil {
		return fmt.Errorf("load subnets: %w", err)
	}
	defer rows.Close()
	for rows.Next() {
		var item Subnet
		if err := rows.Scan(&item.ID, &item.AccountID, &item.AZ, &item.Tier, &item.CIDR); err != nil {
			return err
		}
		c.subnets[item.ID] = item
	}
	if err := rows.Err(); err != nil {
		return err
	}
	images, err := c.db.Query(`SELECT ami_id, owner_account_id, architecture, state, deprecated FROM images`)
	if err != nil {
		return fmt.Errorf("load images: %w", err)
	}
	defer images.Close()
	for images.Next() {
		var item Image
		var deprecated int
		if err := images.Scan(&item.AMIID, &item.Owner, &item.Arch, &item.State, &deprecated); err != nil {
			return err
		}
		item.Deprecated = deprecated != 0
		c.images[item.AMIID] = item
	}
	return images.Err()
}

func (c *Catalog) Subnet(id string) (Subnet, bool) {
	c.mu.Lock()
	defer c.mu.Unlock()
	item, ok := c.subnets[id]
	return item, ok
}

func (c *Catalog) Image(id string) (Image, bool) {
	c.mu.Lock()
	defer c.mu.Unlock()
	item, ok := c.images[id]
	return item, ok
}

func (c *Catalog) EligibleAppSubnet(id, account string) (Subnet, error) {
	item, ok := c.Subnet(id)
	if !ok {
		return Subnet{}, fmt.Errorf("subnet %s is absent from ipam catalog", id)
	}
	if item.AccountID != account {
		return Subnet{}, fmt.Errorf("subnet %s must belong to configured account", id)
	}
	if item.Tier != types.PrivateApp {
		return Subnet{}, fmt.Errorf("subnet %s must have tier private_app", id)
	}
	return item, nil
}

func (c *Catalog) ApprovedImage(amiID, owner, arch string) (Image, error) {
	item, ok := c.Image(amiID)
	if !ok {
		return Image{}, fmt.Errorf("release_artifact.ami_id is absent from ipam images")
	}
	if item.Owner != owner {
		return Image{}, fmt.Errorf("release_artifact.ami_owner_account_id does not match catalog owner")
	}
	if item.Arch != arch {
		return Image{}, fmt.Errorf("release_artifact.architecture does not match catalog architecture")
	}
	if item.State != "available" {
		return Image{}, fmt.Errorf("release_artifact.ami_id must be available")
	}
	if item.Deprecated {
		return Image{}, fmt.Errorf("release_artifact.ami_id must not be deprecated")
	}
	return item, nil
}

func (c *Catalog) SubnetReport(account string) []Subnet {
	c.mu.Lock()
	defer c.mu.Unlock()
	result := make([]Subnet, 0, len(c.subnets))
	for _, item := range c.subnets {
		if account == "" || item.AccountID == account {
			result = append(result, item)
		}
	}
	sort.Slice(result, func(i, j int) bool {
		if result[i].AZ == result[j].AZ {
			return result[i].ID < result[j].ID
		}
		return result[i].AZ < result[j].AZ
	})
	return result
}

func (c *Catalog) PrivateAppIDs(account string) []string {
	ids := []string{}
	for _, item := range c.SubnetReport(account) {
		if item.Tier == types.PrivateApp {
			ids = append(ids, item.ID)
		}
	}
	return ids
}

func (c *Catalog) ImageReport() []Image {
	c.mu.Lock()
	defer c.mu.Unlock()
	result := make([]Image, 0, len(c.images))
	for _, item := range c.images {
		result = append(result, item)
	}
	sort.Slice(result, func(i, j int) bool { return result[i].AMIID < result[j].AMIID })
	return result
}

func (c *Catalog) Counts() map[string]int {
	c.mu.Lock()
	defer c.mu.Unlock()
	tiers := map[string]int{}
	for _, item := range c.subnets {
		tiers[item.Tier]++
	}
	return map[string]int{
		"subnets": len(c.subnets),
		"images":  len(c.images),
		"private_app": tiers[types.PrivateApp],
		"public":      tiers["public"],
	}
}
