import pandas as pd

def read_and_search_csv(file_path, search_column, search_term):
    """
    Reads a CSV file and searches for rows containing the search_term in the given column.

    :param file_path: Path to the CSV file
    :param search_column: Column name to search in
    :param search_term: Keyword or phrase to search for
    :return: Filtered DataFrame
    """
    try:
        # Read CSV file
        df = pd.read_csv(file_path)

        # Validate column existence
        if search_column not in df.columns:
            print(f"Error: Column '{search_column}' not found in CSV.")
            return pd.DataFrame()

        # Case-insensitive search
        filtered_df = df[df[search_column].astype(str).str.contains(search_term, case=False, na=False)]

        return filtered_df

    except FileNotFoundError:
        print(f"Error: File '{file_path}' not found.")
    except pd.errors.EmptyDataError:
        print("Error: CSV file is empty.")
    except Exception as e:
        print(f"Unexpected error: {e}")

    return pd.DataFrame()


# Example usage
if __name__ == "__main__":
    csv_file = "data.csv"  # Replace with your CSV file path
    column_to_search = "Name"  # Replace with the column you want to search
    keyword = "John"  # Replace with your search term

    results = read_and_search_csv(csv_file, column_to_search, keyword)

    if not results.empty:
        print("Search Results:")
        print(results)
    else:
        print("No matching records found.")
