from policy import make_proposal, decide

# try a few cases
print(decide(make_proposal("delete_bucket", "junk1", 0)))       # expect: auto
print(decide(make_proposal("delete_bucket", "junk2", 5)))       # expect: approve
print(decide(make_proposal("delete_bucket", "testsam", 0)))     # expect: block
print(decide(make_proposal("create_bucket", "junk3", 0)))       # expect: block