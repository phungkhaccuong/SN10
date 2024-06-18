
# To run

`fserver_ubuntu` is the binary pre-built for ubuntun 64-bit, you can just start with a port to start the server without building from source.
```
./fserver_ubuntu --port 3001
```

or

```
pm2 start "./fserver_ubuntu --port 10101" -n "wl1001-hk4"
```

Serve axon on the network using custom miner with param similar to normal miner

```
source .venv/bin/activate
python3 neurons/register_miner.py --netuid 10 --wallet.name wl1001 --wallet.hotke hk4 --axon.ip 160.202.129.73 --axon.port 10104 --wandb.off
```


# Building from source

Installing go
```
    wget https://go.dev/dl/go1.22.3.linux-amd64.tar.gz
    sudo tar -C /usr/local -xzf go1.22.3.linux-amd64.tar.gz
    echo "export PATH=\$PATH:/usr/local/go/bin" >> ~/.profile
    source ~/.profile
    go version
```

Build:
```
cd goserver
go mod tidy
go build fserver.go
```

For cached server
```
go build dserver.go
```

# To run
```
go run dserver.go
```
or
```
./dserver.go
```

# To test performance
```
wrk -t1 -c1 -d10s -s request.lua http://160.202.129.73:10203/AllocateAssets
```