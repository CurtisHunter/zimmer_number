import streamlit as st
import pandas as pd
import networkx as nx
from matplotlib import pyplot as plt
import ast

composername_lookup = pd.read_csv("data/composer_lookup.csv")
directorname_lookup = pd.read_csv("data/director_lookup.csv")
main_df = pd.read_csv("data/main_df.csv")
edgelist_df = pd.read_csv('data/edgelist_df.csv')
zimmer_eligible_df = pd.read_csv('data/zimmer_eligible.csv')
tv_lookup = pd.read_csv("data/tv_lookup.csv")

# converting string column to dictionary
main_df['composer_roles'] = main_df['composer_roles'].apply(lambda x: ast.literal_eval(x))

edge_list = [(row.composer1, row.composer2, {'linking_id': row.linking_id}) for row in edgelist_df.itertuples(index=False)]

#graph creation
G = nx.Graph()
G.add_edges_from(edge_list)

def zimmer_number_path(composer, target=947):
    if composer not in G.nodes:
        raise nx.NodeNotFound(f"Source node {composer} is not in the graph")
    if target not in G.nodes:
        raise nx.NodeNotFound(f"Target node {target} is not in the graph")

    # finding shortest path from the source compsoser to Hans Zimmer
    try:
        path = nx.shortest_path(G, source=composer, target=target)
        return path
    except nx.NetworkXNoPath:
        st.write(f"No path exists between {composer} and {target}")
        return None

def plot_zimmer_path(G, center_node, radius=2, path=None): # plots the path from Hans Zimmer to the original composer. Also shows neighbourhood of the original composer
    neighbors = nx.ego_graph(G, center_node, radius=radius)

    if path:
        for node in path:
            if node not in neighbors:
                neighbors.add_node(node)
        for u, v in zip(path, path[1:]):
            if not neighbors.has_edge(u, v):
                # this gets the original edge attributes
                edge_attrs = G[u][v]
                neighbors.add_edge(u, v, **edge_attrs)

    pos = nx.spring_layout(neighbors)
    plt.figure(figsize=(12, 8))

    node_labels = {}
    for node in neighbors.nodes:
        node_labels[node] = composername_lookup[composername_lookup['composer_id'] == node]['composer_name'].iloc[0] # labelling with names instead of ids by using the lookup

    nx.draw(neighbors, pos, with_labels=True, labels=node_labels, node_size=500, node_color="lightblue", font_size=10) # this is where the graph is drawn

    if path:
        path_edges = [(path[i], path[i+1]) for i in range(len(path)-1)]
        for u, v in path_edges:
            if neighbors.has_edge(u, v) and 'linking_id' in neighbors[u][v]:
                linking_id = neighbors[u][v]['linking_id']
                tv_original_name = tv_lookup[tv_lookup['id'] == linking_id]['original_name'].iloc[0]
                st.write(f"{node_labels[u]} -- {tv_original_name} --> {node_labels[v]}")
            else:
                st.write(f"{node_labels[u]} -- ?? --> {node_labels[v]}")

        nx.draw_networkx_nodes(neighbors, pos, nodelist=path, node_color="red", node_size=600)
        nx.draw_networkx_edges(neighbors, pos, edgelist=path_edges, edge_color="red", width=2)

    st.pyplot(plt)


# Filtering to only allow the user to select relevant composers (connected to Hans)
valid_composer_ids = set(G.nodes)
zimmer_eligible_ids = set(zimmer_eligible_df['nodes'])
filtered_composer_ids = valid_composer_ids.intersection(zimmer_eligible_ids)
composername_lookup_filtered = composername_lookup[composername_lookup['composer_id'].isin(filtered_composer_ids)]


st.title("The Zimmer Number")

composer_name = st.selectbox("Search for a composer:", composername_lookup_filtered['composer_name'].tolist())

if composer_name:
    composer_row = composername_lookup_filtered[composername_lookup_filtered['composer_name'].str.contains(composer_name, case=False, na=False)]
    if not composer_row.empty:
        composer_id = composer_row['composer_id'].values[0]
        st.write(f"Composer TMDB ID: {composer_id}")

        target_id = 947 # hans' composer id
        if st.button("Find Zimmer Number"):
            path = zimmer_number_path(composer_id, target=target_id)
            if path:
                st.write("Zimmer Number:", len(path))
                st.write("Visualizing Zimmer Number Graph:")
                st.write("")
                plot_zimmer_path(G, composer_id, radius=2, path=path)
            else:
                st.write("No path found or nodes do not exist in the graph.")
    else:
        st.write("Composer not found.")
else:
    st.write("Enter a composer name to search.")
