# Search directories (list is searched downward until file is found)
# cwd is searched first by default

# Set to get resolver messages through stderr
# (helpful for observing and debugging path resolution)
# setting _more lists every path resolution attempt
resolver_debug = False
resolver_debug_more = False

fhs_dirs = {
"dld": [ #dld directories
    "./dld/",
    "~/dml/dld/",
    "/usr/local/share/dml/dld/",
    "/usr/share/dml/dld/",
    "/etc/dml/dld/"
],
"dss": [ #DSS files
    "./dss/",
    "~/dml/dss/",
    "/usr/local/share/dml/dss/",
    "/usr/share/dml/dss/",
    "/etc/dml/dss/"
]
}


windows_dirs = {
"dld": [],
"dss": []
}
