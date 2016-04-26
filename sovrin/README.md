Refer https://www.digitalocean.com/community/tutorials/how-to-install-and-configure-orientdb-on-ubuntu-14-04 for installing Orient DB

### Initializing Keep
```
init_sovrin_raet_keep --name EvernymV1 --seeds 111111111111111111111111111Alpha Alpha111111111111111111111111111 --force
```

```
init_sovrin_raet_keep --name EvernymV2 --seeds 1111111111111111111111111111Beta Beta1111111111111111111111111111 --force
```

```
init_sovrin_raet_keep --name WSECU --seeds 111111111111111111111111111Gamma Gamma111111111111111111111111111 --force
```

```
init_sovrin_raet_keep --name BIG --seeds 111111111111111111111111111Delta Delta111111111111111111111111111 --force
```

### Seeds used for generating clients
1. Seed used for steward Bob's signing key pair ```11111111111111111111111111111111```
2. Seed used for steward Bob's public private key pair ```33333333333333333333333333333333```
3. Seed used for client Alice's signing key pair ```22222222222222222222222222222222```
4. Seed used for client Alice's public private key pair ```44444444444444444444444444444444```


### Running Node

```
start_sovrin_node Alpha
```