#include "sovereign/checkpoint.hpp"
#include "sovereign/control.hpp"
#include "sovereign/drain.hpp"
#include "sovereign/eligibility.hpp"
#include "sovereign/health.hpp"
#include "sovereign/prober.hpp"
#include "sovereign/proxy.hpp"
#include "sovereign/status.hpp"
#include <atomic>
#include <csignal>
#include <iostream>
#include <thread>
namespace { std::atomic_bool stopping{false}; void signal_handler(int){stopping.store(true);} }
int main(int argc,char** argv){try{std::string config_path="/app/sovereign-lb/config/nodes/dp-01.json";for(int index=1;index<argc;index++){std::string argument=argv[index];if(argument=="--config"&&index+1<argc)config_path=argv[++index];else if(argument=="--help"){std::cout<<"usage: lb-dataplane [--config PATH]\n";return 0;}else throw std::runtime_error("unknown argument: "+argument);}auto config=sovereign::load_node_config(config_path);std::signal(SIGINT,signal_handler);std::signal(SIGTERM,signal_handler);sovereign::RuntimeStore runtimes;sovereign::CheckpointStore checkpoints(config.state_root);if(auto checkpoint=checkpoints.load_current()){runtimes.prepare(checkpoint->snapshot,checkpoint->digest);runtimes.activate(checkpoint->snapshot->generation,checkpoint->digest);}sovereign::Eligibility eligibility;sovereign::HealthTracker health(eligibility);sovereign::DrainManager drains(health);sovereign::ActiveProber prober(runtimes,health);sovereign::Counters counters;sovereign::Proxy proxy(runtimes,eligibility,config.zone,config.max_connections);sovereign::StatusServer status(runtimes,proxy.connections(),counters);sovereign::ControlClient control(config,runtimes,checkpoints,proxy,drains,counters);std::thread status_thread([&]{status.serve(config.status_address,stopping);});std::thread control_thread([&]{control.run(stopping);});std::thread probe_thread([&]{prober.run(stopping);});proxy.run(stopping);control_thread.join();probe_thread.join();status_thread.join();return 0;}catch(const std::exception& error){std::cerr<<"lb-dataplane: "<<error.what()<<"\n";return 1;}}