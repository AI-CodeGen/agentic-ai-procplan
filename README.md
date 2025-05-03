# Agentic AI ProcPlan

This project is a LangChain-based application that uses an agentic AI approach to break down items into their material components and fetch market prices for those materials. It exposes two endpoints via FastAPI and LangServe, and includes a Streamlit UI for local testing.

## Project Structure

- **app/**: Main application package
  - **agents/**: Contains the composition and market agents
  - **main.py**: FastAPI/LangServe app entry point
  - **schemas.py**: Pydantic models for request/response validation
  - **streamlit_ui.py**: Streamlit UI for local testing
  - **swagger.py**: Custom Swagger UI configuration (if needed)

## Requirements

- Python 3.8+
- Dependencies listed in `requirements.txt`

## Setup

1. Create a virtual environment:
   ```bash
   python3 -m venv agentic-pp-venv
   source agentic-pp-venv/bin/activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Running the Application

1. Start the FastAPI app:
   ```bash
   uvicorn app.main:app --reload
   ```

2. Access the Swagger UI at `http://localhost:8000/swagger` to test the API endpoints.

3. Run the Streamlit UI for local testing:
   ```bash
   streamlit run app/streamlit_ui.py
   ```

## Endpoints

- **/v1/composition**: Accepts an item name and returns its material composition.
- **/v1/marketprice**: Accepts a list of materials and returns their market prices.

## Future Enhancements

- Integrate Ollama or another open-source LLM for the composition and market agents.
- Replace mock data with real market data for material prices.

## License

This project is open-source and available under the MIT License. 