"""
Step 8: build the 13-node intra-Asia lead-lag network and rank nodes.

Does:
  - Builds a directed graph from the 24 core edges.
  - Computes out-degree and in-degree per node.
  - Computes eigenvector centrality in both directions: in-edge (follower
    score) and out-edge (leader score, via the reversed graph), plus an
    independent numpy dominant-eigenvector cross-check.

Input:  data/results/granger/granger_significant_links_intra_asia.csv
Output: data/results/network/intra_asia_centrality.csv
"""
import os
import sys
import numpy as np
import pandas as pd
import networkx as nx

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GRANGER = os.path.join(ROOT, "data", "results", "granger")
NETWORK = os.path.join(ROOT, "data", "results", "network")
os.makedirs(NETWORK, exist_ok=True)

NAMES = {
    "2330.TW": "TSMC 台積電", "3711.TW": "ASE 日月光", "6239.TW": "Powertech 力成",
    "2449.TW": "KYEC 京元電子", "3264.TWO": "Ardentec 欣銓", "3037.TW": "Unimicron 欣興",
    "8046.TW": "Nan Ya PCB 南電", "3189.TW": "Kinsus 景碩", "600584.SS": "JCET 長電",
    "002156.SZ": "Tongfu 通富", "002185.SZ": "Huatian 華天", "005930.KS": "Samsung 三星",
    "4062.T": "Ibiden",
}
NODES = list(NAMES.keys())

df = pd.read_csv(os.path.join(GRANGER, "granger_significant_links_intra_asia.csv"))
edges = []
for r in df.itertuples():
    a, b = r.dir1.split("->")
    edges.append((a, b))
    if r.type == "bidirectional":
        c, d = r.dir2.split("->")
        edges.append((c, d))

G = nx.DiGraph()
G.add_nodes_from(NODES)
G.add_edges_from(edges)
out_deg = dict(G.out_degree())
in_deg = dict(G.in_degree())

eig_in = nx.eigenvector_centrality(G, max_iter=2000, tol=1e-10)
GR = G.reverse(copy=True)
eig_out = nx.eigenvector_centrality(GR, max_iter=2000, tol=1e-10)

A = nx.to_numpy_array(G, nodelist=NODES)


def dominant_eig(M):
    vals, vecs = np.linalg.eig(M)
    idx = np.argsort(-vals.real)
    v = vecs[:, idx[0]].real
    if v.sum() < 0:
        v = -v
    return v


vec_in = dominant_eig(A.T)
vec_out = dominant_eig(A)

rows = []
for i, n in enumerate(NODES):
    rows.append(dict(
        ticker=n, name=NAMES[n],
        out_degree=out_deg[n], in_degree=in_deg[n],
        leader_score_outedge_eig=eig_out.get(n, np.nan),
        leader_score_outedge_eig_numpy=vec_out[i],
        follower_score_inedge_eig=eig_in.get(n, np.nan),
        follower_score_inedge_eig_numpy=vec_in[i],
    ))
tab = pd.DataFrame(rows).sort_values("out_degree", ascending=False).reset_index(drop=True)
tab.to_csv(os.path.join(NETWORK, "intra_asia_centrality.csv"), index=False, encoding="utf-8")
print(tab.to_string(index=False))
