import streamlit as st
from sql_optimizer import optimize_sql

# --- PAGE CONFIG ---
st.set_page_config(page_title="SQL Clean", page_icon="🪄")

# --- CORE LOGIC ---
# Using the same logic as your CLI

def get_optimized_sql(sql_input):
    return optimize_sql(sql_input)

# --- UI DESIGN ---
st.title("🪄 SQL Clean")
st.markdown("Transform messy queries into high-performance SQL.")

# Input area
raw_sql = st.text_area("Paste your SQL here:", height=200, placeholder="SELECT * FROM users...")

if st.button("Optimize SQL"):
    if raw_sql.strip():
        with st.spinner("Optimizing..."):
            try:
                optimized = get_optimized_sql(raw_sql)
                
                # Show results in columns
                col1, col2 = st.columns(2)
                with col1:
                    st.subheader("Original")
                    st.code(raw_sql, language="sql")
                with col2:
                    st.subheader("Optimized")
                    st.code(optimized, language="sql")
                    
                st.success("Refactoring complete!")
            except Exception as e:
                st.error(f"Error: {e}")
    else:
        st.warning("Please enter some SQL first.")