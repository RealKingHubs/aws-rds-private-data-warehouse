# Data Warehouse: Cloud RDS Provisioning

A private, network-isolated MySQL database on AWS RDS, provisioned inside a custom VPC and accessed exclusively through a bastion host. Includes schema definition, seed data, and an optional Python client for programmatic queries.

## Features

- Custom VPC with separated public and private subnet tiers across two availability zones
- MySQL 8.4.9 instance on RDS with public accessibility disabled
- Security group rules scoped to a single source (bastion host), not open IP ranges
- Bastion host pattern for secure database access, no direct internet exposure to the database
- SQL schema with primary key, uniqueness, and not-null constraints
- Optional Python client (`scripts/connect_and_query.py`) for querying the database outside the MySQL CLI
- No NAT Gateway dependency, the private subnet has no outbound internet route by design

## Architecture

```
Internet
   |
   v
[Internet Gateway]
   |
   v
[Public Subnet] --- Bastion Host (EC2)
   |
   | (internal VPC traffic, port 3306)
   v
[Private Subnet] --- RDS Instance (MySQL 8.4.9)
```

The RDS instance has no public IP and cannot be reached directly. All access goes through the bastion host, which is the only resource exposed to the internet (restricted to SSH on port 22 from an authorized IP).

## Prerequisites

| Requirement | Version / Notes |
|---|---|
| AWS account | With permissions to create VPC, EC2, RDS, and Security Group resources |
| AWS CLI | v2.x, configured with `aws configure` |
| SSH client | Any standard client (OpenSSH, PuTTY) |
| MySQL client | `mariadb105` package or equivalent, installed on the bastion host |
| Python | 3.9+ (only required for the optional bonus script) |
| pip packages | `pymysql`, `boto3` (only required for the optional bonus script) |

## Quick Start

These steps assume the AWS infrastructure (VPC, subnets, security groups, RDS instance, bastion host) has already been provisioned. See [Infrastructure Setup](#infrastructure-setup) below if starting from zero.

```bash
# 1. Clone the repository
git clone <repository-url>
cd project-3-data-warehouse

# 2. SSH into the bastion host
ssh -i /path/to/your-key.pem ec2-user@<bastion-public-ip>

# 3. Install the MySQL client on the bastion (one-time)
sudo dnf install -y mariadb105

# 4. Connect to the RDS instance
mysql -h <rds-endpoint> -u admin -p

# 5. Run the schema and seed scripts
mysql -h <rds-endpoint> -u admin -p < sql/01_create_table.sql
mysql -h <rds-endpoint> -u admin -p < sql/02_insert_data.sql

# 6. Verify
mysql -h <rds-endpoint> -u admin -p -e "SELECT * FROM warehouse_db.Interns;"
```

## Configuration

The optional Python client (`scripts/connect_and_query.py`) reads its connection details from environment variables. Never hardcode credentials in source files.

| Variable | Required | Description | Example |
|---|---|---|---|
| `RDS_HOST` | Yes | RDS endpoint hostname | `interns-db.xxxxxxxx.us-east-1.rds.amazonaws.com` |
| `RDS_PORT` | No | Database port, defaults to `3306` | `3306` |
| `RDS_USER` | Yes | Database username | `admin` or a scoped-down application user |
| `RDS_PASSWORD` | Yes | Database password | Set via secrets manager or local `.env`, never committed |
| `RDS_DB_NAME` | Yes | Target database name | `warehouse_db` |
| `SSH_KEY_PATH` | Yes (for tunnel scripts) | Path to the `.pem` key used to reach the bastion | `~/.ssh/codela.pem` |
| `BASTION_HOST` | Yes (for tunnel scripts) | Public IP or DNS of the bastion host | `13.220.246.248` |
| `BASTION_USER` | Yes (for tunnel scripts) | SSH username on the bastion | `ec2-user` |

Create a local `.env` file (already covered by `.gitignore`) for local development:

```bash
RDS_HOST=your-rds-endpoint.rds.amazonaws.com
RDS_PORT=3306
RDS_USER=admin
RDS_PASSWORD=your-password-here
RDS_DB_NAME=warehouse_db
SSH_KEY_PATH=~/.ssh/codela.pem
BASTION_HOST=your-bastion-public-ip
BASTION_USER=ec2-user
```

## Infrastructure Setup

Full manual provisioning steps for the VPC, subnets, security groups, RDS instance, and bastion host are documented in [`docs/architecture.md`](docs/architecture.md).

Summary of network resources:

| Resource | Configuration |
|---|---|
| VPC | `10.0.0.0/16` |
| Public subnets | `10.0.1.0/24`, `10.0.2.0/24` (two AZs) |
| Private subnets | `10.0.3.0/24`, `10.0.4.0/24` (two AZs) |
| Internet Gateway | Attached to VPC, routed from public subnets only |
| NAT Gateway | Not used, private subnet has no outbound internet route |
| RDS security group | Allows port `3306` from bastion security group only |
| Bastion security group | Allows port `22` from a single authorized IP only |

## Database Schema

```sql
CREATE TABLE Interns (
  InternID INT PRIMARY KEY,
  FirstName VARCHAR(50) NOT NULL,
  LastName VARCHAR(50) NOT NULL,
  Email VARCHAR(100) UNIQUE NOT NULL
);
```

| Column | Type | Constraints |
|---|---|---|
| `InternID` | `INT` | Primary key |
| `FirstName` | `VARCHAR(50)` | Not null |
| `LastName` | `VARCHAR(50)` | Not null |
| `Email` | `VARCHAR(100)` | Unique, not null |

## Repository Structure

```
project-3-data-warehouse/
├── README.md                                  
├── .gitignore                                 
├── docs/
│   ├── architecture.md                        
│   └── screenshots/
│       ├── 01-rds-config-public-access-off.png
│       ├── 02-security-group-port-3306.png
│       ├── 03-successful-bastion-connection.png
│       ├── 04-table-creation.png
│       ├── 05-select-verification.png
│       └── 06-python-bonus-output.png  
├── sql/
│   ├── 01_create_table.sql
│   └── 02_insert_data.sql
└── scripts/
    ├── connect_and_query.py
    └── requirements.txt   

 ```   

## Security Notes

- RDS public accessibility is disabled. The database has no public IP.
- The RDS security group only accepts inbound traffic from the bastion's security group, not from any IP range.
- The bastion's SSH access is restricted to a single authorized IP, not `0.0.0.0/0`.
- Credentials are never committed. `.pem` keys, `.env` files, and any secrets are excluded via `.gitignore`.
- For application-level access, use a scoped-down database user (`SELECT`, `INSERT` only) rather than the RDS master user. See `sql/03_create_scoped_user.sql` if present.

## Known Issues / Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `ssh: connect to host ... port 22: Connection timed out` | Bastion in a private subnet, or your IP not in the security group's allow list | Confirm bastion is in a public subnet with a public IP; update the security group source to your current IP |
| `ERROR 1046 (3D000): No database selected` | No `USE <database>` statement run before `CREATE TABLE` | Run `CREATE DATABASE warehouse_db; USE warehouse_db;` first |
| `unknown variable 'ssl-mode=VERIFY_IDENTITY'` | Client version does not support that flag syntax | Omit SSL flags; RDS handles encryption without manual configuration for this setup |
| `No match for argument: mysql` (Amazon Linux 2023) | The `mysql` package no longer exists on AL2023 | Install `mariadb105` instead, it is fully compatible as a MySQL client |

## License

Internal training project, DecodeLabs Cloud Computing Internship, Batch 2026.