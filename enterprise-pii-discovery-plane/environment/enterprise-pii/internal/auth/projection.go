package auth

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"sort"
	"strings"

	"enterprise-pii/internal/model"
)

type Authorizer struct { sources map[string]model.Source }
func New(sources []model.Source) *Authorizer { m:=map[string]model.Source{}; for _,s:=range sources{m[s.ID]=s}; return &Authorizer{sources:m} }
func contains(items []string,value string) bool { for _,item:=range items{if item=="*"||item==value{return true}}; return false }
func (a *Authorizer) Can(principal model.Principal, action string, source model.Source) bool {
	if principal.Tenant=="" || !contains(principal.Actions,action){return false}
	if contains(principal.Sources,source.ID){return true}
	return contains(principal.Departments,source.Department)&&contains(principal.Regions,source.Region)
}
func (a *Authorizer) Sources(principal model.Principal, action string) []model.Source { var out []model.Source; for _,source:=range a.sources{if a.Can(principal,action,source){out=append(out,source)}}; sort.Slice(out,func(i,j int)bool{return out[i].ID<out[j].ID}); return out }
func (a *Authorizer) Findings(principal model.Principal, action string, all []model.Finding) []model.Finding { var out []model.Finding; for _,finding:=range all{source,ok:=a.sources[finding.Location.SourceID]; if ok&&a.Can(principal,action,source){out=append(out,finding)}}; return out }
func GrantsDigest(principal model.Principal) string { copy:=principal; sort.Strings(copy.Departments); sort.Strings(copy.Regions); sort.Strings(copy.Sources); sort.Strings(copy.Actions); body,_:=json.Marshal(copy); sum:=sha256.Sum256(body); return hex.EncodeToString(sum[:]) }
type Cursor struct { Principal string `json:"principal"`; GrantsDigest string `json:"grants_digest"`; Generation uint64 `json:"generation"`; QueryDigest string `json:"query_digest"`; Sort string `json:"sort"`; Offset int `json:"offset"` }
func EncodeCursor(cursor Cursor) string { body,_:=json.Marshal(cursor); return hex.EncodeToString(body) }
func DecodeCursor(encoded string, principal model.Principal, generation uint64, queryDigest, order string) (Cursor,error) { body,err:=hex.DecodeString(encoded); if err!=nil{return Cursor{},errors.New("invalid cursor")}; var cursor Cursor; if json.Unmarshal(body,&cursor)!=nil{return Cursor{},errors.New("invalid cursor")}; if cursor.Principal!=principal.ID||cursor.GrantsDigest!=GrantsDigest(principal)||cursor.Generation!=generation||cursor.QueryDigest!=queryDigest||cursor.Sort!=order{return Cursor{},errors.New("cursor authority changed")}; return cursor,nil }
func QueryDigest(parts ...string) string { sum:=sha256.Sum256([]byte(strings.Join(parts,"\x1f"))); return hex.EncodeToString(sum[:]) }