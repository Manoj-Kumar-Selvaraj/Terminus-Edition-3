package main

import (
	"encoding/json"
	"fmt"
	"net/http"
	"os"

	"enterprise-pii/internal/api"
	"enterprise-pii/internal/service"
)

func main(){if len(os.Args)<2{usage()};config:=flag("--config",env("PII_CONFIG","/app/enterprise-pii/config/system.json"));svc,err:=service.Load(config);must(err);switch os.Args[1]{case "serve":must(svc.Recover());server:=&api.Server{Service:svc};must(http.ListenAndServe(svc.Config.Listen,server.Handler()));case "recover":must(svc.Recover());printJSON(svc.Status());case "status":_ = svc.Recover();printJSON(svc.Status());default:usage()}}
func flag(name,fallback string)string{for index,value:=range os.Args{if value==name&&index+1<len(os.Args){return os.Args[index+1]}};return fallback}
func env(name,fallback string)string{if value:=os.Getenv(name);value!=""{return value};return fallback}
func must(err error){if err!=nil{fmt.Fprintln(os.Stderr,err);os.Exit(1)}}
func printJSON(value any){encoder:=json.NewEncoder(os.Stdout);encoder.SetIndent("","  ");must(encoder.Encode(value))}
func usage(){fmt.Fprintln(os.Stderr,"usage: pii-control serve|recover|status [--config FILE]");os.Exit(2)}