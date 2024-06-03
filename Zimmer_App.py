import streamlit as st
import pandas as pd
import networkx as nx
from matplotlib import pyplot as plt
import ast

# Load data
composername_lookup = pd.read_csv("data/composer_lookup.csv")
directorname_lookup = pd.read_csv("data/director_lookup.csv")
main_df = pd.read_csv("data/main_df.csv")
edgelist_df = pd.read_csv('data/edgelist_df.csv')
zimmer_eligible_df = pd.read_csv('data/zimmer_eligible.csv')
tv_lookup = pd.read_csv("data/tv_lookup.csv")

# Convert string column to dictionary
main_df['composer_roles'] = main_df['composer_roles'].apply(lambda x: ast.literal_eval(x))

edge_list = [(row.composer1, row.composer2, {'linking_id': row.linking_id}) for row in edgelist_df.itertuples(index=False)]

# Graph creation
G = nx.Graph()
G.add_edges_from(edge_list)

def zimmer_number_path(composer, target=947):
    if composer not in G.nodes:
        raise nx.NodeNotFound(f"Source node {composer} is not in the graph")
    if target not in G.nodes:
        raise nx.NodeNotFound(f"Target node {target} is not in the graph")

    # Finding shortest path from the source composer to Hans Zimmer
    try:
        path = nx.shortest_path(G, source=composer, target=target)
        return path
    except nx.NetworkXNoPath:
        st.write(f"No path exists between {composer} and {target}")
        return None

def plot_zimmer_path(G, center_node, radius=2, path=None):
    neighbors = nx.ego_graph(G, center_node, radius=radius)

    if path:
        for node in path:
            if node not in neighbors:
                neighbors.add_node(node)
        for u, v in zip(path, path[1:]):
            if not neighbors.has_edge(u, v):
                edge_attrs = G[u][v]
                neighbors.add_edge(u, v, **edge_attrs)

    pos = nx.spring_layout(neighbors)
    plt.figure(figsize=(12, 8))

    node_labels = {}
    for node in neighbors.nodes:
        node_labels[node] = composername_lookup[composername_lookup['composer_id'] == node]['composer_name'].iloc[0]

    nx.draw(neighbors, pos, with_labels=True, labels=node_labels, node_size=500, node_color="lightblue", font_size=10)

    if path:
        path_edges = [(path[i], path[i+1]) for i in range(len(path)-1)]
        nx.draw_networkx_nodes(neighbors, pos, nodelist=path, node_color="red", node_size=600)
        nx.draw_networkx_edges(neighbors, pos, edgelist=path_edges, edge_color="red", width=2)
        st.pyplot(plt)
        for u, v in path_edges:
            if neighbors.has_edge(u, v) and 'linking_id' in neighbors[u][v]:
                linking_id = neighbors[u][v]['linking_id']
                tv_original_name = tv_lookup[tv_lookup['id'] == linking_id]['original_name'].iloc[0]
                st.write(f"{node_labels[u]} -- {tv_original_name} --> {node_labels[v]}")
            else:
                st.write(f"{node_labels[u]} -- ?? --> {node_labels[v]}")

# Filter to only allow the user to select relevant composers (connected to Hans)
valid_composer_ids = set(G.nodes)
zimmer_eligible_ids = set(zimmer_eligible_df['nodes'])
filtered_composer_ids = valid_composer_ids.intersection(zimmer_eligible_ids)
composername_lookup_filtered = composername_lookup[composername_lookup['composer_id'].isin(filtered_composer_ids)]

# Navigation
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["Intro", "The Zimmer Number"])

if page == "Intro":
    st.title("The Zimmer Number")

    st.markdown("""## Intro - The Concept""")

    st.write("Have you heard of the Bacon Number? If not If not, the concept is as follows:")

    st.markdown("- An actor who was in a movie with Kevin Bacon has a Bacon Number of 1.")
    st.markdown("- An actor who was in a movie with someone that has a Bacon Number of 1, has a Bacon Bumber of 2.")
    st.markdown("- An actor who was in a movie with someone that has a Bacon Number of 2, has a Bacon Bumber of 3.")

    st.write("This continues indefinitely.")

    st.image("images/photo2.jpg")

    st.write("")
    st.markdown("""
    Using data that I collected from the TMDB API, I have created **'the Bacon Number' but for composers who have worked with Hans Zimmer!**

    Due to computational limitations, this version of the app only considers **TV show connections**.
    
    The code for this app be found [here](https://github.com/CurtisHunter/zimmer_number/) and the Jupyter notebook for development [here](https://github.com/CurtisHunter/zimmer_number/blob/main/tmdb%20network%20setup%20and%20EDA.ipynb).
    """)

    st.image("images/photo1.jpg")

    st.write("")

    st.markdown("""### Example of a composer with a Zimmer Number of 3""")

    st.image("images/photo3.jpg", width = 200)

    st.write("")

    st.write("""Click on 'The Zimmer Number' on the left hand side to try it for yourself! If you can't see that, press the '>' button in the top left.""")

elif page == "The Zimmer Number":
    st.markdown("""## Calculate the Zimmer Number""")

    composername_lookup_filtered_sorted = composername_lookup_filtered.sort_values(by='popularity', ascending=False)
    composer_names_sorted = composername_lookup_filtered_sorted['composer_name'].tolist()
    composer_name = st.selectbox("Search for a composer (sorted by popularity):", composer_names_sorted)

    if composer_name:
        composer_row = composername_lookup_filtered[composername_lookup_filtered['composer_name'].str.contains(composer_name, case=False, na=False)]
        if not composer_row.empty:
            composer_id = composer_row['composer_id'].values[0]

            target_id = 947 # Hans' composer ID
            if st.button("Find Link!"):
                path = zimmer_number_path(composer_id, target=target_id)
                if path:
                    st.markdown(f"""### Zimmer Number: {len(path) - 1}""")
                    st.write("")
                    plot_zimmer_path(G, composer_id, radius=2, path=path)
                else:
                    st.write("No path found or nodes do not exist in the graph.")
        else:
            st.write("Composer not found.")
    else:
        st.write("Enter a composer name to search.")

    for i in range(10): # Adding some spacing
        st.write("")

    st.markdown("""
    ## Acknowledgements
    
    [TMDB](https://www.themoviedb.org/) is the source of all of the data
    """)
