package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"strings"
)

func main(){if len(os.Args)<2{usage()};base:=option("--endpoint","http://127.0.0.1:8080");var method,path string;var body any;switch os.Args[1]{case "health":method,path="GET","/health";case "metrics":method,path="GET","/v1/status";case "source":require(3);method,path="GET","/v1/sources";case "policy":require(3);method,path="GET","/v1/policies";case "worker":require(3);method,path="GET","/v1/status";case "job":require(3);id:=option("--id","");switch os.Args[2]{case "create":method,path="POST","/v1/jobs";body=map[string]string{"id":id,"policy_version":option("--policy","")+"","corpus_digest":option("--corpus-digest","")};case "cancel":method,path="POST","/v1/jobs/"+id+"/cancel";case "status":method,path="GET","/v1/jobs/"+id;default:usage()};case "report":require(3);id:=option("--job","");if os.Args[2]=="show"{method,path="GET","/v1/reports/"+id}else if os.Args[2]=="export"{method,path="GET","/v1/reports/"+id+"/export?format="+option("--format","json")}else{usage()};default:usage()};request(method,base+path,body)}
func request(method,url string,value any){var reader io.Reader;if value!=nil{body,_:=json.Marshal(value);reader=bytes.NewReader(body)};request,err:=http.NewRequest(method,url,reader);must(err);request.Header.Set("Content-Type","application/json");response,err:=http.DefaultClient.Do(request);must(err);defer response.Body.Close();_,_=io.Copy(os.Stdout,response.Body);if response.StatusCode>=400{os.Exit(1)}}
func option(name,fallback string)string{for index,value:=range os.Args{if value==name&&index+1<len(os.Args){return os.Args[index+1]}};return fallback}
func require(count int){if len(os.Args)<count{usage()}}
func must(err error){if err!=nil{fmt.Fprintln(os.Stderr,err);os.Exit(1)}}
func usage(){fmt.Fprintln(os.Stderr,"usage: piictl health|metrics|source list|policy list|worker list|job create|cancel|status|report show|export");os.Exit(2)}
var _ = strings.Builder{}