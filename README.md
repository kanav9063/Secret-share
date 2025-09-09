```mermaid
graph TD
    A[CLI Client] --> B[FastAPI Backend]
    B --> C[SQLite Database]
    B --> D[GitHub OAuth]
    A --> E[Browser] --> D
    D --> B
```
