package persistence

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strconv"
	"strings"
	"time"
)

type Entry struct { Name string `json:"name"`; Size int64 `json:"size"`; SHA256 string `json:"sha256"` }
type GenerationManifest struct { Schema string `json:"schema"`; Generation uint64 `json:"generation"`; CreatedAt time.Time `json:"created_at"`; Entries []Entry `json:"entries"` }
type RetentionLease struct { ID string `json:"id"`; Generations []uint64 `json:"generations"`; ExpiresAt time.Time `json:"expires_at"`; Reason string `json:"reason"` }
type Store struct { Root string; Retain int }
func New(root string,retain int)*Store{return &Store{Root:root,Retain:retain}}
func generationName(number uint64)string{return fmt.Sprintf("%020d",number)}
func hash(body []byte)string{sum:=sha256.Sum256(body);return hex.EncodeToString(sum[:])}

func (s *Store) Publish(number uint64, files map[string][]byte, now time.Time) error {
	if number==0{return errors.New("generation must be positive")}
	base:=filepath.Join(s.Root,"generations"); if err:=os.MkdirAll(base,0755);err!=nil{return err}
	temporary:=filepath.Join(base,"."+generationName(number)+".tmp"); final:=filepath.Join(base,generationName(number)); _=os.RemoveAll(temporary); if err:=os.Mkdir(temporary,0755);err!=nil{return err}
	names:=make([]string,0,len(files));for name:=range files{names=append(names,name)};sort.Strings(names)
	manifest:=GenerationManifest{Schema:"enterprise-pii-state/v1",Generation:number,CreatedAt:now.UTC()}
	for _,name:=range names{if filepath.Base(name)!=name{return errors.New("nested state entry")}; body:=files[name]; if err:=os.WriteFile(filepath.Join(temporary,name),body,0644);err!=nil{return err}; manifest.Entries=append(manifest.Entries,Entry{Name:name,Size:int64(len(body)),SHA256:hash(body)})}
	body,err:=json.Marshal(manifest);if err!=nil{return err};if err=os.WriteFile(filepath.Join(temporary,"manifest.json"),body,0644);err!=nil{return err}
	if err=s.VerifyPath(temporary);err!=nil{return err};if err=os.Rename(temporary,final);err!=nil{return err}
	currentTemp:=filepath.Join(s.Root,"CURRENT.tmp");if err=os.WriteFile(currentTemp,[]byte(generationName(number)+"\n"),0644);err!=nil{return err};return os.Rename(currentTemp,filepath.Join(s.Root,"CURRENT"))
}

func (s *Store) VerifyPath(path string)error{body,err:=os.ReadFile(filepath.Join(path,"manifest.json"));if err!=nil{return err};var manifest GenerationManifest;if json.Unmarshal(body,&manifest)!=nil{return errors.New("invalid generation manifest")};for _,entry:=range manifest.Entries{content,err:=os.ReadFile(filepath.Join(path,entry.Name));if err!=nil||int64(len(content))!=entry.Size||hash(content)!=entry.SHA256{return errors.New("generation content mismatch")}};return nil}
func (s *Store) Recover()(uint64,map[string][]byte,error){base:=filepath.Join(s.Root,"generations");entries,err:=os.ReadDir(base);if err!=nil{return 0,nil,err};var numbers []uint64;for _,entry:=range entries{if !entry.IsDir(){continue};number,err:=strconv.ParseUint(entry.Name(),10,64);if err==nil{numbers=append(numbers,number)}};sort.Slice(numbers,func(i,j int)bool{return numbers[i]>numbers[j]});for _,number:=range numbers{path:=filepath.Join(base,generationName(number));if s.VerifyPath(path)!=nil{continue};manifestBody,_:=os.ReadFile(filepath.Join(path,"manifest.json"));var manifest GenerationManifest;_ = json.Unmarshal(manifestBody,&manifest);files:=map[string][]byte{};for _,entry:=range manifest.Entries{files[entry.Name],_=os.ReadFile(filepath.Join(path,entry.Name))};return number,files,nil};return 0,nil,errors.New("no valid generation")}
func (s *Store) ReadCurrent()(uint64,error){body,err:=os.ReadFile(filepath.Join(s.Root,"CURRENT"));if err!=nil{return 0,err};name:=strings.TrimSpace(string(body));number,err:=strconv.ParseUint(name,10,64);if err!=nil{return 0,err};if s.VerifyPath(filepath.Join(s.Root,"generations",generationName(number)))!=nil{return 0,errors.New("current generation invalid")};return number,nil}
func (s *Store) Cleanup(protected map[uint64]bool,leases []RetentionLease,now time.Time)([]uint64,error){for _,lease:=range leases{if lease.ExpiresAt.After(now){for _,number:=range lease.Generations{protected[number]=true}}};base:=filepath.Join(s.Root,"generations");entries,err:=os.ReadDir(base);if err!=nil{return nil,err};var numbers []uint64;for _,entry:=range entries{number,err:=strconv.ParseUint(entry.Name(),10,64);if err==nil{numbers=append(numbers,number)}};sort.Slice(numbers,func(i,j int)bool{return numbers[i]>numbers[j]});var removed []uint64;kept:=0;for _,number:=range numbers{if protected[number]||kept<s.Retain{kept++;continue};if err:=os.RemoveAll(filepath.Join(base,generationName(number)));err!=nil{return removed,err};removed=append(removed,number)};return removed,nil}