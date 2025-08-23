-- 添加 CompletionRate 字段到 Contracts 表
ALTER TABLE Contracts ADD CompletionRate DECIMAL(5,2) DEFAULT 0.00;

-- 创建 FixedCosts 表
CREATE TABLE FixedCosts (
    FixedCostID INT IDENTITY(1,1) PRIMARY KEY,
    CostType NVARCHAR(100) NOT NULL,
    Amount DECIMAL(18,2) NOT NULL,
    CostDate DATE,
    Description NVARCHAR(500),
    Month NVARCHAR(7) NOT NULL,
    CreatedDate DATETIME DEFAULT GETDATE()
);