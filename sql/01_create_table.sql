CREATE DATABASE warehouse_db;
USE warehouse_db;

CREATE TABLE Interns (
  InternID INT PRIMARY KEY,
  FirstName VARCHAR(50) NOT NULL,
  LastName VARCHAR(50) NOT NULL,
  Email VARCHAR(100) UNIQUE NOT NULL
);