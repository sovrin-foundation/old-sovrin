def testAnonCredFlow(nodeSet, client1, addedIssuer, addedVerifier,
                     addedProver, looper):
    "Testing bootstrapping of Issuer, Prover and Verifier"
    assert all((client1.issuer, client1.prover, client1.verifier))
