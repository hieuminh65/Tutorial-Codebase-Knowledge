# Chapter 7: Data Schemas & Persistence

In [Chapter 6: gRPC & Protocol Buffers](06_grpc___protocol_buffers_.md), we learned how our different microservices (Account, Catalog, Order) talk to each other using a fast and reliable communication system (gRPC) based on shared contracts (`.proto` files).

But what happens when you create a new user account? Or when a customer places an order? Where does that information go? If the service restarts, how does it remember the accounts and orders? Simply keeping information in the computer's temporary memory isn't enough – we need to store it somewhere permanent. This is where **Data Schemas & Persistence** come in.

## The Need for Permanent Storage

Imagine you sign up for our online store. The [Account Service](03_account_service_.md) creates your account. Later, you come back to log in. The service needs to *remember* you! Similarly, when you place an order, the [Order Service](05_order_service_.md) needs to record that order so it can be processed and viewed later in your history.

If the information was only stored in the service's temporary memory (RAM), it would disappear if the service crashed or was restarted. We need a way to make the data **persist**, meaning it sticks around even when the service isn't running.

This is achieved by using a **database**. Think of a database as a dedicated digital filing cabinet designed for storing and retrieving information efficiently and reliably.

## Separate Filing Cabinets: Service-Owned Data

In our microservice architecture, each service that needs to store data permanently gets its *own* database.
*   The [Account Service](03_account_service_.md) has its own database for user accounts.
*   The [Order Service](05_order_service_.md) has its own database for order information.
*   The [Catalog Service](04_catalog_service_.md) (in a more complex setup) would likely have its own database for products, though in this specific project, it might load data differently – but the principle holds.

Why separate databases? Think back to our company analogy. HR (Account Service) has its own confidential employee records, and Sales (Order Service) has its own customer order files. They don't share the same filing cabinet because their data is distinct and they manage it independently. This keeps things organized and prevents one department's changes from messing up another's records.

```mermaid
graph LR
    A[Account Service] --> AD(Account Database)
    O[Order Service] --> OD(Order Database)
    C[Catalog Service] --> CD(Catalog Database)
    G[API Gateway] --- A
    G --- O
    G --- C
    O --> C  // Order Service talks to Catalog Service
    A -.-> |Owns| AD
    O -.-> |Owns| OD
    C -.-> |Owns| CD
```
*(Diagram: Shows each service connecting to its own dedicated database.)*

## The Blueprint: Data Schemas (`.sql` files)

Okay, so each service has a database (a filing cabinet). But how does the database know *how* to organize the data? How does it know what an "account" looks like or what information belongs in an "order"?

This is defined by the **Data Schema**. The schema is like the detailed blueprint for the filing cabinet – it specifies the drawers (tables), the folders within each drawer (rows), and the exact labels and types of information allowed on each folder (columns and data types).

In our project, these schemas are defined in files ending with `.sql`. SQL (Structured Query Language) is the standard language used to interact with many databases, especially relational databases like PostgreSQL (which we use here).

Let's look at the schema for the Account Service:

```sql
-- File: account/up.sql

-- Create a 'table' named 'accounts' if it doesn't exist
CREATE TABLE IF NOT EXISTS accounts (
  -- Column 1: 'id', a fixed-length text, must be unique (PRIMARY KEY)
  id CHAR(27) PRIMARY KEY,

  -- Column 2: 'name', variable-length text (up to 24 chars), cannot be empty (NOT NULL)
  name VARCHAR(24) NOT NULL
);
```

**Explanation:**

*   `CREATE TABLE IF NOT EXISTS accounts`: This tells the database: "Create a table (like a spreadsheet or a drawer in the cabinet) called `accounts`, but only if one doesn't already exist."
*   `id CHAR(27) PRIMARY KEY`: This defines the first column (like a labeled section on a folder).
    *   `id`: The name of the column.
    *   `CHAR(27)`: The type of data it holds - fixed-length text, 27 characters long.
    *   `PRIMARY KEY`: This is crucial! It means the value in the `id` column *must be unique* for every row (every account). It's the unique identifier, like an employee ID number.
*   `name VARCHAR(24) NOT NULL`: This defines the second column.
    *   `name`: The name of the column.
    *   `VARCHAR(24)`: The type of data - variable-length text, with a maximum of 24 characters.
    *   `NOT NULL`: This means this field *must* have a value; it cannot be left empty when creating an account.

This simple `.sql` file precisely defines the structure for storing account data in the Account Service's database.

Now let's look at the Order Service's schema, which is a bit more complex because an order can contain multiple products:

```sql
-- File: order/up.sql (Part 1: Orders Table)

-- Create the main table for order information
CREATE TABLE IF NOT EXISTS orders (
  id CHAR(27) PRIMARY KEY,                -- Unique ID for the order itself
  created_at TIMESTAMP WITH TIME ZONE NOT NULL, -- When the order was placed
  account_id CHAR(27) NOT NULL,          -- Links to the account ID (from Account Service)
  total_price MONEY NOT NULL            -- The final calculated price
);

-- File: order/up.sql (Part 2: Order Products Table)

-- Create a table to store which products are in which order
CREATE TABLE IF NOT EXISTS order_products (
  -- Links this entry back to a specific order in the 'orders' table
  order_id CHAR(27) REFERENCES orders (id) ON DELETE CASCADE,
  product_id CHAR(27),                  -- The ID of the product included
  quantity INT NOT NULL,                -- How many of this product were ordered
  -- A product can only appear once per order
  PRIMARY KEY (product_id, order_id)
);
```

**Explanation:**

*   **`orders` table:** Stores one row for each order, containing the order's unique `id`, when it was created (`created_at`), who placed it (`account_id`), and the `total_price`.
*   **`order_products` table:** This table connects orders to products.
    *   `order_id CHAR(27) REFERENCES orders (id)`: This is important. It links each row in this table back to a specific order in the `orders` table using the `order_id`. `REFERENCES orders (id)` sets up this relationship. `ON DELETE CASCADE` means if an order is deleted from the `orders` table, the corresponding items in this table are automatically deleted too.
    *   `product_id CHAR(27)`: Stores the ID of the product included in the order.
    *   `quantity INT NOT NULL`: Stores how many units of that product were ordered (an integer number).
    *   `PRIMARY KEY (product_id, order_id)`: A combined key ensuring that the same product ID cannot be listed twice within the same order ID.

These `.sql` files provide the blueprint that the database uses to structure the stored information.

## Setting Up the Database (The `db.dockerfile`)

How do these databases actually get created and configured with the schemas? We use Docker for this too! Each service that needs a database has a corresponding `db.dockerfile`.

Let's look at the one for the Account service:

```dockerfile
# File: account/db.dockerfile

# Use an official PostgreSQL database image (version 10.3)
FROM postgres:10.3

# Copy our schema file into a special directory in the image.
# Files in this directory are automatically run when the database starts for the first time.
COPY up.sql /docker-entrypoint-initdb.d/1.sql

# Default command to start the PostgreSQL server
CMD ["postgres"]
```

**Explanation:**

1.  `FROM postgres:10.3`: Starts with a pre-built Docker image containing PostgreSQL version 10.3.
2.  `COPY up.sql /docker-entrypoint-initdb.d/1.sql`: This is the magic step. It copies our `account/up.sql` schema file into a specific folder (`/docker-entrypoint-initdb.d/`) inside the PostgreSQL image. The official PostgreSQL image is configured to automatically run any `.sql` files found in this directory when the database container starts for the *first time*.
3.  `CMD ["postgres"]`: Specifies the command to run when the container starts, which is simply starting the PostgreSQL server.

So, when we run the project (using Docker Compose, which orchestrates starting all our containers), Docker will:
1.  Start a new PostgreSQL container based on the `account/db.dockerfile`.
2.  The PostgreSQL container sees `1.sql` (which is our `up.sql`) in the initialization directory.
3.  It runs the SQL commands in that file, creating the `accounts` table.
4.  The database is now ready for the Account Service to use!

The same process happens for the Order Service with its `order/db.dockerfile` and `order/up.sql`.

## How Services Use the Database

Once the database is set up with the correct schema, the service's Go code can interact with it. When the Account Service needs to create a new account, its Go code will:
1.  Establish a connection to its dedicated Account Database.
2.  Construct an SQL `INSERT` command, something like:
    `INSERT INTO accounts (id, name) VALUES ('some_unique_id', 'Alice');`
3.  Send this command to the database.
4.  The database executes the command, adding a new row to the `accounts` table.

Similarly, to find an account by ID, the service would use an SQL `SELECT` command:
`SELECT id, name FROM accounts WHERE id = 'some_unique_id';`

And the Order Service would use `INSERT` commands for both the `orders` and `order_products` tables when creating a new order, and `SELECT` commands (potentially joining the two tables) when retrieving order history.

(We won't dive deep into the specific Go database/sql library code here, but understand that the Go code in each service is responsible for sending these SQL commands to *its own* database based on the logic required by gRPC requests.)

## Conclusion

In this chapter, we learned about the importance of **persistence** – making data last beyond the lifetime of a service. We saw how:

*   Microservices that need to store data (like Account and Order) typically use their **own dedicated databases**.
*   **Data Schemas**, defined in `.sql` files, act as the blueprint, specifying the structure (tables, columns, data types) for storing data within a database.
*   We use Docker (via `db.dockerfile` and the PostgreSQL image's initialization process) to automatically set up these databases and apply the schemas when the system starts.
*   Each service's Go code interacts with its database using SQL commands (`INSERT`, `SELECT`, etc.) to store and retrieve the data it manages.

This approach of separate, schema-defined databases ensures that each microservice truly owns and manages its own data, reinforcing the independence and organizational benefits of the microservice architecture.

You've now covered the core concepts of this project: the overall [Microservice Architecture](01_microservice_architecture_.md), the [GraphQL API Gateway](02_graphql_api_gateway_.md) entry point, the individual services ([Account Service](03_account_service_.md), [Catalog Service](04_catalog_service_.md), [Order Service](05_order_service_.md)), the internal communication mechanism ([gRPC & Protocol Buffers](06_grpc___protocol_buffers_.md)), and finally, how data is stored using [Data Schemas & Persistence](07_data_schemas___persistence_.md). Congratulations on completing the conceptual overview!

---

Generated by [AI Codebase Knowledge Builder](https://github.com/The-Pocket/Tutorial-Codebase-Knowledge)