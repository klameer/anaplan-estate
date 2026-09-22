"""Build the Caldergate example estate: four fictional Anaplan models written
as the three grid exports the tool reads (Line Items, Modules, Actions).

The estate is fictional and built to look inherited: two consultancies,
three build years, one leftover module, a formula nobody dares touch, an
import from a hub that no longer exists. Every planted fault is listed in
examples/caldergate-estate/PLANTED.md, and the report should find each one.

Run:  python examples/build_caldergate_estate.py
Then: anaplan-estate examples/caldergate-estate --out estate.md

Referenced By is computed from the parsed formulas, so the agreement check
in the report reads 100 percent; on a real export it is Anaplan's column.
"""
from __future__ import annotations
import csv, json, sys, pathlib, hashlib, re
from dataclasses import dataclass, field

ROOT = pathlib.Path(__file__).resolve().parent
OUT = ROOT / "caldergate-estate"
sys.path.insert(0, str(ROOT.parent / "src"))
from anaplan_estate.model import load_model          # noqa: E402
from anaplan_estate.graph import build_graph          # noqa: E402

# ---------------------------------------------------------------- shapes

DIMS = {
    "Cost Centres": 133, "Cost Centre Groups": 12, "Departments": 18, "Accounts": 262,
    "P&L Lines": 14, "Products": 42, "Segments": 6, "Regions": 6, "Legal Entities": 4,
    "Currencies": 8, "Employees": 1850, "Roles": 31, "Customers": 480, "Asset Classes": 5,
    "Account Types": 6, "Scenarios": 5,
}
TIME = {"Month": 36, "Quarter": 12, "Year": 3, "Not Applicable": 1}
VERSIONS = {"All": 4, "Not Applicable": 1}     # Actual, Forecast, Budget, Budget v2 DO NOT USE

FMT = {
    "NUMBER": '{"minimumSignificantDigits":4,"decimalPlaces":-1,"decimalSeparator":"FULL_STOP","groupingSeparator":"COMMA","negativeNumberNotation":"MINUS_SIGN","unitsType":"NONE","unitsDisplayType":"NONE","zeroFormat":"ZERO","comparisonIncrease":"GOOD","dataType":"NUMBER"}',
    "PCT": '{"minimumSignificantDigits":4,"decimalPlaces":1,"decimalSeparator":"FULL_STOP","groupingSeparator":"COMMA","negativeNumberNotation":"MINUS_SIGN","unitsType":"PERCENTAGE","unitsDisplayType":"PERCENTAGE","zeroFormat":"ZERO","comparisonIncrease":"GOOD","dataType":"NUMBER"}',
    "BOOLEAN": '{"dataType":"BOOLEAN"}',
    "TEXT": '{"textType":"GENERAL","dataType":"TEXT"}',
    "DATE": '{"dataType":"DATE"}',
    "TIME": '{"periodType":"MONTH","dataType":"TIME_ENTITY"}',
}
def LIST(name):  # list-formatted line item; the id is fictional
    h = int(hashlib.md5(name.encode()).hexdigest()[:8], 16) % 900 + 100
    return '{"hierarchyEntityLongId":101000000%03d,"selectiveAccessApplied":false,"showAll":true,"dataType":"ENTITY"}' % h

SUMMARY = {
    "SUM": '{"summaryMethod":"SUM","timeSummaryMethod":"SUM","timeSummarySameAsMainSummary":true}',
    "NONE": '{"summaryMethod":"NONE","timeSummaryMethod":"NONE","timeSummarySameAsMainSummary":true}',
    "FORMULA": '{"summaryMethod":"FORMULA","timeSummaryMethod":"FORMULA","timeSummarySameAsMainSummary":true}',
    "CLOSING": '{"summaryMethod":"SUM","timeSummaryMethod":"CLOSING_BALANCE","timeSummarySameAsMainSummary":false}',
    "ANY": '{"summaryMethod":"ANY","timeSummaryMethod":"ANY","timeSummarySameAsMainSummary":true}',
    "": "",
}

LI_COLS = ["", "Format", "Formula", "Summary", "Applies To", "Time Scale", "Time Range", "Versions", "Style", "Cell Count",
           "Calculation Effort", "Notes", "Read Access Driver", "Write Access Driver", "Users List", "Parent", "Is Summary",
           "Formula Scope", "Code", "Use Switchover", "Breakback", "Brought-Forward", "Start of Section", "Data Tags",
           "Referenced By", "Module Name"]
MOD_COLS = ["", "Functional Area", "Applies To", "Time Scale", "Time Range", "Versions", "Breakback", "Users List", "Cell Count",
            "Notes", "Read Access Driver", "Write Access Driver", "Data Tags", "Managed By", "Referenced By", "Used in Dashboards", "Line Items"]
ACT_COLS = ["", "Action", "Start Date and Time (UTC)", "Most recent duration (ms)", "Notes", "Used in Processes", "Used in Dashboards"]


@dataclass
class LI:
    name: str
    fmt: str = "NUMBER"          # key of FMT, or LIST(...) json
    formula: str = ""
    applies: tuple | None = None # None = module's; () = none; else override (subsidiary view)
    ts: str | None = None        # None = module's
    vers: str | None = None
    summary: str | None = None   # None = SUM for numbers, NONE otherwise
    notes: str = ""
    style: str = ""


@dataclass
class Mod:
    name: str
    fa: str
    applies: tuple = ()
    ts: str = "Month"
    vers: str = "All"
    notes: str = ""
    items: list = field(default_factory=list)


@dataclass
class Act:
    name: str
    kind: str                    # import | export | other | process
    target: str = ""
    last: str = ""
    ms: int = 0
    procs: tuple = ()
    detail: str = ""
    notes: str = ""


@dataclass
class ModelDef:
    folder: str
    modules: list
    processes: dict              # name -> (last_run, ms, [steps])
    actions: list
    effort: bool = True


def N(name, formula="", **kw): return LI(name, "NUMBER", formula, **kw)
def P(name, formula="", **kw): return LI(name, "PCT", formula, **kw)
def B(name, formula="", **kw): return LI(name, "BOOLEAN", formula, **kw)
def T(name, formula="", **kw): return LI(name, "TEXT", formula, **kw)
def D(name, formula="", **kw): return LI(name, "DATE", formula, **kw)
def L(name, lst, formula="", **kw): return LI(name, LIST(lst), formula, **kw)


# ---------------------------------------------------------------- model 1: data hub (2019, first partner)

def data_hub() -> ModelDef:
    mods = [
        Mod("SYS01 Time Settings", "System", (), "Month", "Not Applicable", "Standard time flags. Built Mar 2019.", [
            B("Current Period?", "ITEM(Time) = 'SYS00 Model Settings'.Current Period", summary="NONE"),
            D("Start of Month", "START()", summary="NONE"),
            D("End of Month", "END()", summary="NONE"),
            N("Days in Month", "DAYS()", summary="NONE"),
            T("Period Label", "NAME(ITEM(Time))", summary="NONE"),
        ]),
        Mod("SYS00 Model Settings", "System", (), "Not Applicable", "Not Applicable", "", [
            LI("Current Period", "TIME", summary="NONE"),
            LI("Last Loaded Period", "TIME", summary="NONE"),
            T("Load Status", '"OK"', summary="NONE"),
        ]),
        Mod("DAT01 GL Transactions", "Data", ("Cost Centres", "Accounts"), "Month", "Not Applicable", "Loaded daily from NetSuite. Do not enter data here.", [
            N("Amount"),
            N("Journal Count", summary="SUM"),
            T("Source System", summary="NONE"),
            B("Loaded?", "Journal Count > 0", summary="ANY"),
        ]),
        Mod("DAT02 Cost Centre Master", "Data", ("Cost Centres",), "Not Applicable", "Not Applicable", "", [
            L("Department", "Departments"), L("Region", "Regions"), L("Legal Entity", "Legal Entities"), L("Currency", "Currencies"),
            B("Active?"), T("Cost Centre Code", "CODE(ITEM(Cost Centres))"), T("Description"),
            L("Group", "Cost Centre Groups", "PARENT(ITEM(Cost Centres))"),
            T("Owner Email"),
        ]),
        Mod("DAT03 Account Master", "Data", ("Accounts",), "Not Applicable", "Not Applicable", "", [
            L("Account Type", "Account Types"), L("P&L Line", "P&L Lines"), T("Account Code", "CODE(ITEM(Accounts))"),
            B("Revenue?", "Account Type = Account Types.Revenue"), B("Opex?", "Account Type = Account Types.Opex"),
            B("COGS?", "Account Type = Account Types.COGS"), N("Sign", "IF Revenue? THEN -1 ELSE 1"),
        ]),
        Mod("DAT04 Product Master", "Data", ("Products",), "Not Applicable", "Not Applicable", "", [
            L("Segment", "Segments"), D("Launch Date"), B("Active?"), T("Product Code", "CODE(ITEM(Products))"),
            L("Revenue Cost Centre", "Cost Centres"), T("Product Family"),
        ]),
        Mod("DAT05 CRM Pipeline", "Data", ("Customers",), "Month", "Not Applicable", "", [
            N("Open Pipeline"), P("Probability"), N("Weighted Pipeline", "Open Pipeline * Probability"),
            D("Expected Close"), L("Stage", "Scenarios"),
        ]),
        Mod("DAT06 Sales Orders", "Data", ("Customers", "Products"), "Month", "Not Applicable", "", [
            N("Units"), N("Order Revenue"), N("Order Count"), T("Last Order Ref", summary="NONE"),
        ]),
        Mod("DAT07 Customer Master", "Data", ("Customers",), "Not Applicable", "Not Applicable", "", [
            L("Region", "Regions"), L("Segment", "Segments"), T("Customer Code", "CODE(ITEM(Customers))"), B("Key Account?"),
            T("Region Code", "CODE(Region)"),
        ]),
        Mod("DAT08 Employee Master", "Data", ("Employees",), "Not Applicable", "Not Applicable", "Loaded from Workday. WFP model loads Workday separately (see Workforce Planning).", [
            L("Cost Centre", "Cost Centres"), L("Role", "Roles"), D("Start Date"), D("End Date"), N("FTE"), T("Employee Id", "CODE(ITEM(Employees))"),
        ]),
        Mod("CAL01 Volume Summary", "Calculation", ("Products", "Regions"), "Month", "Not Applicable", "", [
            N("Units", "'DAT06 Sales Orders'.Units[SUM: 'DAT07 Customer Master'.Region]"),
            N("Revenue", "'DAT06 Sales Orders'.Order Revenue[SUM: 'DAT07 Customer Master'.Region]"),
            N("Orders", "'DAT06 Sales Orders'.Order Count[SUM: 'DAT07 Customer Master'.Region]"),
            N("Average Order Value", "DIVIDE(Revenue, Orders)", summary="FORMULA"),
        ]),
        Mod("SYS02 Data Checks", "System", (), "Month", "Not Applicable", "Reconciliation flags read by the load dashboard.", [
            N("GL Total", "'DAT01 GL Transactions'.Amount"),
            N("Orders Total", "'DAT06 Sales Orders'.Order Revenue"),
            N("Difference", "GL Total - Orders Total"),
            B("Within Tolerance?", "ABS(Difference) < 1000", summary="ANY"),
            T("Check Message", 'IF Within Tolerance? THEN "OK" ELSE "GL and orders differ by " & TEXT(Difference)', summary="NONE"),
        ]),
    ]
    procs = {
        "Daily Load": ("2026-09-21 05:02:14", 41800, ["Import GL from NetSuite", "Import Orders from Salesforce", "Import Pipeline from Salesforce"]),
        "Monthly Master Data": ("2026-09-01 06:10:44", 9200, ["Import Cost Centres from NetSuite", "Import Accounts from NetSuite", "Import Employees from Workday"]),
        "Publish to Spokes": ("2026-09-21 05:03:01", 14100, ["Export GL to FP&A", "Export Volumes to FP&A", "Export Cost Centre Map to Workforce", "Export Product Master to FP&A", "Export Account Master to FP&A"]),
    }
    acts = [
        Act("Import GL from NetSuite", "import", "DAT01 GL Transactions", "2026-09-21 05:02:14", 38900, ("Daily Load",)),
        Act("Import Orders from Salesforce", "import", "DAT06 Sales Orders", "2026-09-21 05:02:53", 2100, ("Daily Load",)),
        Act("Import Pipeline from Salesforce", "import", "DAT05 CRM Pipeline", "2026-09-21 05:02:55", 800, ("Daily Load",)),
        Act("Import Cost Centres from NetSuite", "import", "DAT02 Cost Centre Master", "2026-09-01 06:10:44", 600, ("Monthly Master Data",)),
        Act("Import Accounts from NetSuite", "import", "DAT03 Account Master", "2026-09-01 06:10:45", 400, ("Monthly Master Data",)),
        Act("Import Employees from Workday", "import", "DAT08 Employee Master", "2026-09-01 06:10:46", 8200, ("Monthly Master Data",)),
        Act("Import Products from PIM file", "import", "DAT04 Product Master", "2023-06-14 11:22:09", 300, (), notes="Manual. PIM extract from Marketing."),
        Act("Import Customers from Salesforce", "import", "DAT07 Customer Master", "2026-08-30 17:41:02", 1900, ()),
        Act("Export GL to FP&A", "export", "DAT01 GL Transactions", "2026-09-21 05:03:01", 9800, ("Publish to Spokes",)),
        Act("Export Volumes to FP&A", "export", "CAL01 Volume Summary", "2026-09-21 05:03:11", 1200, ("Publish to Spokes",)),
        Act("Export Cost Centre Map to Workforce", "export", "DAT02 Cost Centre Master", "2026-09-21 05:03:12", 300, ("Publish to Spokes",)),
        Act("Export Product Master to FP&A", "export", "DAT04 Product Master", "2026-09-21 05:03:13", 200, ("Publish to Spokes",)),
        Act("Export Account Master to FP&A", "export", "DAT03 Account Master", "2026-09-21 05:03:13", 200, ("Publish to Spokes",)),
        Act("Export Pipeline for Sales Ops", "export", "DAT05 CRM Pipeline", "2025-02-11 09:15:40", 700, ()),
    ]
    return ModelDef("1 Caldergate Data Hub", mods, procs, acts)


# ---------------------------------------------------------------- model 2: FP&A (2019, first partner, DISCO naming)

OPEX_DRIVERS = ["Rent", "Business Rates", "Utilities", "Cleaning", "Security", "Insurance", "Travel", "Subsistence", "Mileage",
                "Hotels", "Marketing Events", "Marketing Digital", "Marketing Print", "Agency Fees", "Software Licences",
                "Software Support", "Hardware", "Telecoms", "Mobile", "Postage", "Stationery", "Printing", "Legal Fees",
                "Audit Fees", "Consultancy", "Contractors", "Recruitment Fees", "Training", "Subscriptions", "Memberships",
                "Bank Charges", "Vehicle Lease", "Fuel", "Repairs", "Maintenance Contracts", "Waste", "Uniforms", "Safety Equipment",
                "Entertaining", "Gifts", "Donations", "Sponsorship", "Research", "Samples", "Freight Out", "Packaging",
                "Warehouse Rent", "Temp Labour", "Overtime Premium", "Other Opex"]

def fpa() -> ModelDef:
    inp02 = [N(d) for d in OPEX_DRIVERS] + [
        N("Total Drivers", " + ".join(OPEX_DRIVERS), notes="Ugly but right. Sums every driver; add new drivers here too."),
        N("Property Costs", "Rent + Business Rates + Utilities + Cleaning + Security + Insurance"),
        N("People Costs", "Travel + Subsistence + Mileage + Hotels + Training + Recruitment Fees"),
        N("Marketing Costs", "Marketing Events + Marketing Digital + Marketing Print + Agency Fees + Sponsorship"),
        N("IT Costs", "Software Licences + Software Support + Hardware + Telecoms + Mobile"),
        N("Check", "Total Drivers - Property Costs - People Costs - Marketing Costs - IT Costs", notes="Should equal 'other' drivers. Nobody looks at it."),
        B("Has Drivers?", "Total Drivers <> 0", summary="ANY"),
        N("Driver Count", "IF Has Drivers? THEN 1 ELSE 0"),
    ]
    # CAL12: one line per driver, phased by the Actual? flag. Copy-paste module; makes Actual? the hub.
    phased = [N(f"{d} Phased", f"IF 'SYS01 Time Settings'.Actual? THEN 0 ELSE 'INP02 Opex Drivers'.{d}") for d in OPEX_DRIVERS[:30]]
    phased.append(N("Total Phased", " + ".join(f"{d} Phased" for d in OPEX_DRIVERS[:30])))
    # CAL03: the 12-branch IF that maps drivers to accounts
    acct_map = [("6100 Rent", "Rent"), ("6110 Rates", "Business Rates"), ("6120 Utilities", "Utilities"), ("6200 Travel", "Travel"),
                ("6210 Subsistence", "Subsistence"), ("6300 Marketing", "Marketing Events"), ("6310 Digital", "Marketing Digital"),
                ("6400 Software", "Software Licences"), ("6410 Hardware", "Hardware"), ("6500 Professional Fees", "Consultancy"),
                ("6510 Audit", "Audit Fees"), ("6600 Recruitment", "Recruitment Fees")]
    ifs = "".join(f"IF ITEM(Accounts) = Accounts.'{a}' THEN 'INP02 Opex Drivers'.{d} ELSE " for a, d in acct_map) + "0"
    # CAL10: the 400-character formula that works
    dep = ("IF ISBLANK('INP04 Capex'.Asset Class) THEN 0 ELSE "
           "IF 'INP04 Capex'.Useful Life Years = 3 THEN MOVINGSUM('INP04 Capex'.Capex Spend, -35, 0) / 36 ELSE "
           "IF 'INP04 Capex'.Useful Life Years = 5 THEN MOVINGSUM('INP04 Capex'.Capex Spend, -59, 0) / 60 ELSE "
           "IF 'INP04 Capex'.Useful Life Years = 7 THEN MOVINGSUM('INP04 Capex'.Capex Spend, -83, 0) / 84 ELSE "
           "IF 'INP04 Capex'.Useful Life Years = 10 THEN MOVINGSUM('INP04 Capex'.Capex Spend, -119, 0) / 120 ELSE "
           "IF 'INP04 Capex'.Useful Life Years > 10 THEN MOVINGSUM('INP04 Capex'.Capex Spend, -239, 0) / 240 ELSE "
           "'INP04 Capex'.Capex Spend / 12")
    mods = [
        Mod("SYS00 Model Settings", "System", (), "Not Applicable", "Not Applicable", "", [
            LI("Current Period", "TIME", summary="NONE"), LI("Forecast Start", "TIME", summary="NONE"), LI("Model Start", "TIME", summary="NONE"),
            L("Reporting Currency", "Currencies", summary="NONE"), P("Default VAT Rate", summary="NONE"),
            N("NI Threshold", summary="NONE", notes="Annual. Update each April."), P("NI Rate", summary="NONE"),
            P("Corporation Tax Rate", summary="NONE"), B("Lock Actuals?", summary="NONE"),
        ]),
        Mod("SYS01 Time Settings", "System", (), "Month", "Not Applicable", "Time flags. Every calc module reads Actual? from here.", [
            B("Current Period?", "ITEM(Time) = 'SYS00 Model Settings'.Current Period", summary="NONE"),
            B("Actual?", "ITEM(Time) < 'SYS00 Model Settings'.Forecast Start", summary="NONE"),
            B("Forecast?", "NOT Actual?", summary="NONE"),
            B("First Period?", "ITEM(Time) = 'SYS00 Model Settings'.Model Start", summary="NONE"),
            D("Start of Month", "START()", summary="NONE"), D("End of Month", "END()", summary="NONE"),
            N("Days in Month", "DAYS()", summary="NONE"), N("Weekend Days", summary="NONE"), N("Bank Holidays", summary="NONE"),
            N("Working Days", "Days in Month - Weekend Days - Bank Holidays", summary="NONE"),
            T("Month Name", "NAME(ITEM(Time))", summary="NONE"),
            N("Year", "YEAR(START())", summary="NONE"),
            N("Period Number", "MONTH(START())", summary="NONE"),
        ]),
        Mod("SYS02 Cost Centre Attributes", "System", ("Cost Centres",), "Not Applicable", "Not Applicable", "", [
            L("Department", "Departments"), L("Region", "Regions"), L("Legal Entity", "Legal Entities"), L("Currency", "Currencies"),
            B("Active?"), T("Cost Centre Code", "CODE(ITEM(Cost Centres))"), L("Group", "Cost Centre Groups", "PARENT(ITEM(Cost Centres))"),
            T("Owner"), T("Region Code", "CODE(Region)"), T("CC and Region", 'Cost Centre Code & " - " & Region Code'),
            B("Sales CC?", "Department = Departments.Sales"),
        ]),
        Mod("SYS03 Account Attributes", "System", ("Accounts",), "Not Applicable", "Not Applicable", "", [
            L("Account Type", "Account Types"), L("P&L Line", "P&L Lines"), T("Account Code", "CODE(ITEM(Accounts))"),
            B("Revenue?", "Account Type = Account Types.Revenue"), B("Opex?", "Account Type = Account Types.Opex"),
            B("COGS?", "Account Type = Account Types.COGS"), B("Staff?", "Account Type = Account Types.Staff"),
            N("Sign", "IF Revenue? THEN -1 ELSE 1"),
        ]),
        Mod("SYS04 Product Attributes", "System", ("Products",), "Not Applicable", "Not Applicable", "", [
            L("Segment", "Segments"), D("Launch Date"), B("Active?"), T("Product Code", "CODE(ITEM(Products))"),
            L("Revenue Cost Centre", "Cost Centres"), T("Product Family"),
        ]),
        Mod("SYS05 FX Rates", "System", ("Currencies",), "Month", "All", "Rates to GBP. Loaded from Treasury file monthly (manual).", [
            N("Rate to GBP", summary="NONE"), B("Rate Locked?", summary="NONE"),
            N("Rate to GBP Prior", "PREVIOUS(Rate to GBP)", summary="NONE"),
            P("Rate Movement", "DIVIDE(Rate to GBP - Rate to GBP Prior, Rate to GBP Prior)", summary="NONE"),
        ]),
        Mod("SYS06 Region Attributes", "System", ("Regions",), "Not Applicable", "Not Applicable", "", [
            L("Currency", "Currencies"), T("Region Code", "CODE(ITEM(Regions))"), T("Region Manager"), B("Reportable?"),
        ]),
        Mod("SYS07 Launch Flags", "System", ("Products",), "Month", "Not Applicable", "", [
            B("Launched?", "START() >= 'SYS04 Product Attributes'.Launch Date", summary="NONE"),
            N("Months Since Launch", "IF Launched? THEN YEAR(START()) * 12 + MONTH(START()) - YEAR('SYS04 Product Attributes'.Launch Date) * 12 - MONTH('SYS04 Product Attributes'.Launch Date) ELSE 0", summary="NONE"),
        ]),
        Mod("INP01 Volumes", "Input", ("Products", "Regions"), "Month", "All", "", [
            N("Units"), N("Price", summary="NONE"), P("Discount %", summary="NONE"), P("Returns %", summary="NONE"),
            N("Volume Override"), B("Use Override?", summary="NONE"), T("Comment", summary="NONE"),
        ]),
        Mod("INP02 Opex Drivers", "Input", ("Cost Centres",), "Month", "All", "", inp02),
        Mod("INP03 Headcount", "Input", ("Cost Centres", "Roles"), "Month", "All", "Imported from Workforce Planning monthly. Salary is annual.", [
            N("FTE"), N("Salary", summary="NONE"), P("Bonus %", summary="NONE"),
            N("Monthly Salary", "Salary / 12"),
            N("NI Threshold", "'SYS00 Model Settings'.NI Threshold / 12", summary="NONE"),
            N("NI Rate", "'SYS00 Model Settings'.NI Rate", summary="NONE"),
            N("Employer NI", "IF Monthly Salary > NI Threshold THEN (Monthly Salary - NI Threshold) * NI Rate ELSE 0"),
            N("Bonus", "Monthly Salary * Bonus %"),
            N("Pension", "Monthly Salary * 0.05"),
            N("Total Cost", "(Monthly Salary + Employer NI + Bonus + Pension) * FTE"),
        ]),
        Mod("INP04 Capex", "Input", ("Cost Centres",), "Month", "All", "", [
            N("Capex Spend"), N("Useful Life Years", summary="NONE"), L("Asset Class", "Asset Classes", summary="NONE"), T("Project", summary="NONE"),
        ]),
        Mod("INP05 Balance Sheet Drivers", "Input", ("Legal Entities",), "Month", "All", "", [
            N("Debtor Days", summary="NONE"), N("Creditor Days", summary="NONE"), N("Stock Days", summary="NONE"),
            N("Opening Cash Balance", summary="NONE"), P("Tax Rate Override", summary="NONE"),
        ]),
        Mod("INP06 Unit Costs", "Input", ("Products",), "Month", "All", "", [
            N("Unit Cost", summary="NONE"), N("Freight per Unit", summary="NONE"), N("Landed Cost", "Unit Cost + Freight per Unit", summary="NONE"),
        ]),
        Mod("DAT01 Actuals GL", "Data", ("Cost Centres", "Accounts"), "Month", "All", "Landed from the Data Hub. Versions: only Actual is loaded.", [
            N("Amount"), T("Source Journal", summary="NONE"),
            L("Journal Cost Centre", "Cost Centres", "FINDITEM(Cost Centres, Source Journal)", summary="NONE"),
            B("Loaded?", "Amount <> 0", summary="ANY"),
        ]),
        Mod("DAT02 Actuals Volumes", "Data", ("Products", "Regions"), "Month", "All", "", [
            N("Units Actual"), N("Revenue Actual"),
        ]),
        Mod("CAL01 Volumes", "Calculation", ("Products", "Regions"), "Month", "All", "", [
            N("Units", "IF 'SYS01 Time Settings'.Actual? THEN 'DAT02 Actuals Volumes'.Units Actual ELSE IF 'INP01 Volumes'.Use Override? THEN 'INP01 Volumes'.Volume Override ELSE 'INP01 Volumes'.Units"),
            N("Returns", "Units * 'INP01 Volumes'.Returns %"),
            N("Net Units", "Units - Returns"),
            B("Launched?", "'SYS07 Launch Flags'.Launched?", applies=("Products",), summary="NONE", notes="Subsidiary view. Cheaper than a lookup, said the builder."),
            N("Sellable Units", "IF Launched? THEN Net Units ELSE 0"),
            N("Sellable Units Prior Year", "LAG(Sellable Units, 12, 0)"),
            P("Volume Growth", "DIVIDE(Sellable Units - Sellable Units Prior Year, Sellable Units Prior Year)", summary="FORMULA"),
        ]),
        Mod("CAL02 Revenue", "Calculation", ("Products", "Regions"), "Month", "All", "", [
            N("Gross Revenue", "'CAL01 Volumes'.Sellable Units * 'INP01 Volumes'.Price"),
            N("Discounts", "Gross Revenue * 'INP01 Volumes'.Discount %"),
            N("Net Revenue", "Gross Revenue - Discounts"),
            N("Revenue GBP", "Net Revenue * 'SYS05 FX Rates'.Rate to GBP[LOOKUP: 'SYS06 Region Attributes'.Currency]"),
            N("Revenue USD", "Revenue GBP * 1.27", notes="Board wants USD. Rate agreed with Treasury Jan 2024."),
            N("VAT", "Net Revenue * 0.2"),
            N("Revenue per Unit", "Net Revenue / 'CAL01 Volumes'.Net Units", summary="FORMULA"),
            N("Average Price", "DIVIDE(Net Revenue, 'CAL01 Volumes'.Net Units)", summary="FORMULA"),
            T("Actual or Forecast", "IF 'SYS01 Time Settings'.Actual? THEN \"Actual\" ELSE \"Forecast\"", summary="NONE"),
            T("Revenue Label", "NAME(ITEM(Products)) & \" / \" & NAME(ITEM(Regions))", summary="NONE"),
            N("Revenue Prior Year", "LAG(Revenue GBP, 12, 0)"),
            P("Revenue Growth", "DIVIDE(Revenue GBP - Revenue Prior Year, Revenue Prior Year)", summary="FORMULA"),
        ]),
        Mod("CAL03 Opex", "Calculation", ("Cost Centres", "Accounts"), "Month", "All", "", [
            N("Actual Opex", "IF 'SYS03 Account Attributes'.Opex? THEN 'DAT01 Actuals GL'.Amount ELSE 0"),
            N("Forecast Opex", ifs, notes="One branch per driver account. Add a branch when Finance adds an account."),
            N("Opex", "IF 'SYS01 Time Settings'.Actual? THEN Actual Opex ELSE Forecast Opex"),
            N("Opex GBP", "Opex * 'SYS05 FX Rates'.Rate to GBP[LOOKUP: 'SYS02 Cost Centre Attributes'.Currency]"),
            N("Opex Prior Year", "LAG(Opex GBP, 12, 0)"),
            N("Opex Variance", "Opex GBP - Opex Prior Year"),
        ]),
        Mod("CAL04 Margn", "Calculation", ("Products", "Regions"), "Month", "All", "", [
            N("COGS", "'CAL01 Volumes'.Sellable Units * 'INP06 Unit Costs'.Landed Cost"),
            N("Margin", "'CAL02 Revenue'.Net Revenue - COGS"),
            P("Margin %", "DIVIDE(Margin, 'CAL02 Revenue'.Net Revenue)", summary="FORMULA"),
            N("Margin GBP", "Margin * 'SYS05 FX Rates'.Rate to GBP[LOOKUP: 'SYS06 Region Attributes'.Currency]"),
        ]),
        Mod("CAL05 Opex OLD", "Calculation", ("Cost Centres", "Accounts"), "Month", "All", "Replaced by CAL03 in 2021. Keep until the FY22 audit is closed.", [
            N(f"{n}", f) for n, f in [
                ("Actual", "IF 'SYS01 Time Settings'.Actual? THEN 'DAT01 Actuals GL'.Amount ELSE 0"),
                ("Rent Forecast", "IF ITEM(Accounts) = Accounts.'6100 Rent' THEN 'INP02 Opex Drivers'.Rent ELSE 0"),
                ("Rates Forecast", "IF ITEM(Accounts) = Accounts.'6110 Rates' THEN 'INP02 Opex Drivers'.Business Rates ELSE 0"),
                ("Utilities Forecast", "IF ITEM(Accounts) = Accounts.'6120 Utilities' THEN 'INP02 Opex Drivers'.Utilities ELSE 0"),
                ("Travel Forecast", "IF ITEM(Accounts) = Accounts.'6200 Travel' THEN 'INP02 Opex Drivers'.Travel ELSE 0"),
                ("Marketing Forecast", "IF ITEM(Accounts) = Accounts.'6300 Marketing' THEN 'INP02 Opex Drivers'.Marketing Events ELSE 0"),
                ("Software Forecast", "IF ITEM(Accounts) = Accounts.'6400 Software' THEN 'INP02 Opex Drivers'.Software Licences ELSE 0"),
                ("Fees Forecast", "IF ITEM(Accounts) = Accounts.'6500 Professional Fees' THEN 'INP02 Opex Drivers'.Consultancy ELSE 0"),
                ("Other Forecast", "IF ITEM(Accounts) = Accounts.'6900 Other' THEN 'INP02 Opex Drivers'.Other Opex ELSE 0"),
                ("Forecast", "Rent Forecast + Rates Forecast + Utilities Forecast + Travel Forecast + Marketing Forecast + Software Forecast + Fees Forecast + Other Forecast"),
                ("Opex", "IF 'SYS01 Time Settings'.Actual? THEN Actual ELSE Forecast"),
                ("Opex GBP", "Opex * 'SYS05 FX Rates'.Rate to GBP[LOOKUP: 'SYS02 Cost Centre Attributes'.Currency]"),
                ("Opex Cumulative", "CUMULATE(Opex GBP)"),
                ("Opex Run Rate", "MOVINGSUM(Opex GBP, -2, 0) / 3"),
            ]
        ]),
        Mod("CAL06 Department Summary", "Calculation", ("Departments",), "Month", "All", "", [
            N("Revenue", "'CAL07 P&L by Cost Centre'.Revenue[SUM: 'SYS02 Cost Centre Attributes'.Department]"),
            N("Opex", "'CAL07 P&L by Cost Centre'.Opex[SUM: 'SYS02 Cost Centre Attributes'.Department]"),
            N("Staff Cost", "'CAL07 P&L by Cost Centre'.Staff Cost[SUM: 'SYS02 Cost Centre Attributes'.Department]"),
            N("FTE", "'INP03 Headcount'.FTE[SUM: 'SYS02 Cost Centre Attributes'.Department]"),
            N("Benchmark Opex", "'CAL03 Opex'.Opex GBP[SUM: 'SYS02 Cost Centre Attributes'.Department, LOOKUP: 'SYS09 Department Settings'.Benchmark Account]", notes="temp fix for Q3 close, remove later"),
            N("Cost per FTE", "DIVIDE(Opex + Staff Cost, FTE)", summary="FORMULA"),
        ]),
        Mod("SYS09 Department Settings", "System", ("Departments",), "Not Applicable", "Not Applicable", "", [
            L("Benchmark Account", "Accounts"), T("Head of Department"), B("Cost Centre Owner Approves?"),
        ]),
        Mod("CAL07 P&L by Cost Centre", "Calculation", ("Cost Centres",), "Month", "All", "The P&L every report reads. Lines in P&L order.", [
            N("Revenue", "'CAL02 Revenue'.Revenue GBP[SUM: 'SYS04 Product Attributes'.Revenue Cost Centre]"),
            N("COGS", "'CAL04 Margn'.COGS[SUM: 'SYS04 Product Attributes'.Revenue Cost Centre]"),
            N("Gross Margin", "Revenue - COGS"),
            N("Opex", "'CAL03 Opex'.Opex GBP"),
            N("Staff Cost", "'INP03 Headcount'.Total Cost"),
            N("EBITDA", "Gross Margin - Opex - Staff Cost"),
            N("Depreciation", "'CAL10 Depreciation'.Charge"),
            N("EBIT", "EBITDA - Depreciation"),
            P("EBITDA Margin", "DIVIDE(EBITDA, Revenue)", summary="FORMULA"),
            N("Opex Budget", "Opex[SELECT: VERSIONS.Budget]"),
            N("Opex Variance to Budget", "Opex - Opex Budget"),
        ]),
        Mod("CAL08 Cash Flow", "Calculation", ("Legal Entities",), "Month", "All", "", [
            N("EBITDA", "'CAL07 P&L by Cost Centre'.EBITDA[SUM: 'SYS02 Cost Centre Attributes'.Legal Entity]"),
            N("Revenue", "'CAL07 P&L by Cost Centre'.Revenue[SUM: 'SYS02 Cost Centre Attributes'.Legal Entity]"),
            N("Debtors", "Revenue * 'INP05 Balance Sheet Drivers'.Debtor Days / 30"),
            N("Working Capital Movement", "Debtors - PREVIOUS(Debtors)"),
            N("Tax", "IF EBITDA > 0 THEN EBITDA * 0.25 ELSE 0"),
            N("Capex", "'INP04 Capex'.Capex Spend[SUM: 'SYS02 Cost Centre Attributes'.Legal Entity]"),
            N("Net Cash Flow", "EBITDA - Tax - Capex - Working Capital Movement"),
            N("Opening Cash", "IF 'SYS01 Time Settings'.First Period? THEN 'INP05 Balance Sheet Drivers'.Opening Cash Balance ELSE PREVIOUS(Closing Cash)", summary="NONE"),
            N("Closing Cash", "Opening Cash + Net Cash Flow", summary="CLOSING"),
            B("Cash Negative?", "Closing Cash < 0", summary="ANY"),
        ]),
        Mod("CAL09 Scenario Planning", "Calculation", ("Scenarios",), "Month", "All", "", []),
        Mod("CAL10 Depreciation", "Calculation", ("Cost Centres",), "Month", "All", "", [
            N("Charge", dep, notes="DO NOT TOUCH. Reconciles to the fixed asset register to the pound. Built by Priya, 2020."),
            N("NBV", "CUMULATE('INP04 Capex'.Capex Spend) - CUMULATE(Charge)", summary="CLOSING"),
        ]),
        Mod("CAL11 Reporting Prep", "Calculation", ("Cost Centres",), "Month", "All", "", [
            N("Revenue", "'CAL07 P&L by Cost Centre'.Revenue"),
            N("EBITDA", "'CAL07 P&L by Cost Centre'.EBITDA"),
            N("Opex", "'CAL07 P&L by Cost Centre'.Opex"),
            N("Staff Cost", "'CAL07 P&L by Cost Centre'.Staff Cost"),
            N("Total Cost", "Opex + Staff Cost"),
        ]),
        Mod("CAL12 Driver Phasing", "Calculation", ("Cost Centres",), "Month", "All", "", phased),
        Mod("OUT01 Management Pack", "Output", ("Cost Centres",), "Month", "All", "Read by the Management Pack page and the export.", [
            N("Revenue", "'CAL11 Reporting Prep'.Revenue"),
            N("EBITDA", "'CAL11 Reporting Prep'.EBITDA"),
            N("Opex", "'CAL11 Reporting Prep'.Opex"),
            N("Staff Cost", "'CAL11 Reporting Prep'.Staff Cost"),
            N("Total Cost", "'CAL11 Reporting Prep'.Total Cost"),
            N("Headcount", "'INP03 Headcount'.FTE"),
            N("Capex", "'INP04 Capex'.Capex Spend"),
            N("Depreciation", "'CAL10 Depreciation'.Charge"),
            N("Revenue YTD", "YEARTODATE(Revenue)"),
            N("EBITDA YTD", "YEARTODATE(EBITDA)"),
            N("Phased Drivers", "'CAL12 Driver Phasing'.Total Phased"),
        ]),
        Mod("OUT02 Board Pack", "Output", ("Cost Centres",), "Month", "All", "", [
            N("Revenue", "'OUT01 Management Pack'.Revenue"),
            N("EBITDA", "'OUT01 Management Pack'.EBITDA"),
            N("Budget Revenue", "'OUT01 Management Pack'.Revenue[SELECT: VERSIONS.Budget]"),
            N("Old Budget Revenue", "'OUT01 Management Pack'.Revenue[SELECT: VERSIONS.'Budget v2 DO NOT USE']", notes="Q3 2023 restatement. Board pack still shows both. Ask Dan before removing."),
            N("Revenue Variance", "Revenue - Budget Revenue"),
            P("Revenue Variance %", "DIVIDE(Revenue Variance, Budget Revenue)", summary="FORMULA"),
        ]),
    ]
    procs = {
        "Monthly Actuals Load": ("2026-09-03 07:30:12", 61200, ["Import from Caldergate Data Hub - GL Actuals", "Import from Caldergate Data Hub - Volumes"]),
        "Master Data Refresh": ("2026-09-01 07:10:03", 4100, ["Import from Caldergate Data Hub - Cost Centres", "Import from Caldergate Data Hub - Products", "Import from Caldergate Data Hub - Accounts"]),
        "Headcount Refresh": ("2026-09-05 09:12:47", 7700, ["Import from Workforce Planning - Headcount Cost"]),
        "Publish Board Pack": ("2026-09-08 16:02:19", 5300, ["Export Board Pack", "Export P&L to Board Reporting"]),
        "Roll Forecast": ("2026-09-03 07:35:00", 2900, ["Clear Forecast Overrides", "Copy Actual to Forecast"]),
    }
    acts = [
        Act("Import from Caldergate Data Hub - GL Actuals", "import", "DAT01 Actuals GL", "2026-09-03 07:30:12", 58400, ("Monthly Actuals Load",)),
        Act("Import from Caldergate Data Hub - Volumes", "import", "DAT02 Actuals Volumes", "2026-09-03 07:31:10", 2600, ("Monthly Actuals Load",)),
        Act("Import from Caldergate Data Hub - Cost Centres", "import", "SYS02 Cost Centre Attributes", "2026-09-01 07:10:03", 900, ("Master Data Refresh",)),
        Act("Import from Caldergate Data Hub - Products", "import", "SYS04 Product Attributes", "2026-09-01 07:10:04", 400, ("Master Data Refresh",)),
        Act("Import from Caldergate Data Hub - Accounts", "import", "SYS03 Account Attributes", "2026-09-01 07:10:05", 300, ("Master Data Refresh",)),
        Act("Import from Workforce Planning - Headcount Cost", "import", "INP03 Headcount", "2026-09-05 09:12:47", 7700, ("Headcount Refresh",)),
        Act("Import FX from Treasury file", "import", "SYS05 FX Rates", "2023-11-02 10:41:55", 300, (), notes="Manual upload. Treasury sends the file on the 1st."),
        Act("Import from Caldergate Hub v1 - Cost Centres", "import", "SYS02 Cost Centre Attributes", "2021-03-19 14:05:22", 0, (), notes="Old hub. Replaced by Data Hub Mar 2021."),
        Act("Import Budget from Excel", "import", "INP02 Opex Drivers", "2025-11-20 15:22:08", 4400, ()),
        Act("Export Board Pack", "export", "OUT02 Board Pack", "2026-09-08 16:02:19", 3100, ("Publish Board Pack",)),
        Act("Export P&L to Board Reporting", "export", "CAL07 P&L by Cost Centre", "2026-09-08 16:02:23", 2200, ("Publish Board Pack",)),
        Act("Export Assumptions for Workforce", "export", "SYS00 Model Settings", "2026-09-05 09:10:02", 100, ()),
        Act("Export Opex Drivers to Excel", "export", "INP02 Opex Drivers", "2024-05-30 11:00:41", 900, ()),
        Act("Clear Forecast Overrides", "other", "", "2026-09-03 07:35:00", 1200, ("Roll Forecast",), detail='{"actionType":"DELETE_BY_SELECTION","hierarchyIdentifier":"_101000000023","lineItemIdentifier":"_201000000811"}'),
        Act("Copy Actual to Forecast", "other", "", "2026-09-03 07:35:02", 1700, ("Roll Forecast",), detail="Import into 'INP01 Volumes'"),
    ]
    return ModelDef("2 Caldergate FP&A", mods, procs, acts)


# ---------------------------------------------------------------- model 3: workforce (2021, second partner, own naming)

def workforce() -> ModelDef:
    mods = [
        Mod("Inputs - Settings", "Inputs", (), "Not Applicable", "Not Applicable", "", [
            LI("Current Period", "TIME", summary="NONE"), LI("Forecast Start", "TIME", summary="NONE"),
            N("NI Threshold", summary="NONE"), P("NI Rate", summary="NONE"), P("Pension Rate", summary="NONE"),
            P("Salary Inflation", summary="NONE"), LI("Inflation Month", "TIME", summary="NONE"),
        ]),
        Mod("Inputs - Calendar", "Inputs", (), "Month", "Not Applicable", "", [
            B("Current Period?", "ITEM(Time) = 'Inputs - Settings'.Current Period", summary="NONE"),
            B("Actual?", "ITEM(Time) < 'Inputs - Settings'.Forecast Start", summary="NONE"),
            N("Days in Month", "DAYS()", summary="NONE"), N("Weekend Days", summary="NONE"), N("Bank Holidays", summary="NONE"),
            N("Working Days", "Days in Month - Weekend Days - Bank Holidays", summary="NONE"),
            B("Inflation Applies?", "ITEM(Time) >= 'Inputs - Settings'.Inflation Month", summary="NONE"),
        ]),
        Mod("Data - Cost Centre Map", "Data", ("Cost Centres",), "Not Applicable", "Not Applicable", "From the Data Hub.", [
            L("Department", "Departments"), L("Region", "Regions"), B("Active?"), T("CC Code", "CODE(ITEM(Cost Centres))"),
        ]),
        Mod("Data - Employees", "Data", ("Employees",), "Month", "Not Applicable", "Workday extract, monthly. One row per employee per month.", [
            T("Employee Name", summary="NONE"), L("Cost Centre", "Cost Centres", summary="NONE"), L("Role", "Roles", summary="NONE"),
            N("Salary", summary="NONE"), D("Start Date", summary="NONE"), D("End Date", summary="NONE"), N("FTE"),
            B("Active?", "START() >= Start Date AND (ISBLANK(End Date) OR START() <= End Date)", summary="ANY"),
            T("Name and Role", "Employee Name & \" (\" & NAME(Role) & \")\"", summary="NONE"),
            B("Leaver This Month?", "NOT ISBLANK(End Date) AND End Date >= START() AND End Date <= END()", summary="ANY"),
        ]),
        Mod("Calcs - Cost", "Calcs", ("Employees",), "Month", "All", "", [
            N("Salary", "'Data - Employees'.Salary", summary="NONE"),
            N("Monthly Salary", "IF 'Data - Employees'.Active? THEN Salary / 12 ELSE 0"),
            N("Inflated Salary", "IF 'Inputs - Calendar'.Inflation Applies? THEN Monthly Salary * (1 + 'Inputs - Settings'.Salary Inflation) ELSE Monthly Salary"),
            N("NI Threshold", "'Inputs - Settings'.NI Threshold / 12", summary="NONE"),
            N("NI Rate", "'Inputs - Settings'.NI Rate", summary="NONE"),
            N("Employer NI", "IF Monthly Salary > NI Threshold THEN (Monthly Salary - NI Threshold) * NI Rate ELSE 0"),
            N("Pension", "Inflated Salary * 'Inputs - Settings'.Pension Rate"),
            N("Bonus", "Inflated Salary * 0.1"),
            N("Total Cost", "Inflated Salary + Employer NI + Pension + Bonus"),
        ]),
        Mod("Calcs - Headcount by CC", "Calcs", ("Cost Centres", "Roles"), "Month", "All", "Exported to FP&A INP03.", [
            N("FTE", "'Data - Employees'.FTE[SUM: 'Data - Employees'.Cost Centre, SUM: 'Data - Employees'.Role]"),
            N("Total Cost", "'Calcs - Cost'.Total Cost[SUM: 'Data - Employees'.Cost Centre, SUM: 'Data - Employees'.Role]"),
            N("Salary", "'Calcs - Cost'.Inflated Salary[SUM: 'Data - Employees'.Cost Centre, SUM: 'Data - Employees'.Role] * 12"),
            N("Average Salary", "DIVIDE(Salary, FTE)", summary="FORMULA"),
            P("Bonus %", "0.1", summary="NONE"),
        ]),
        Mod("Calcs - Attrition", "Calcs", ("Roles",), "Month", "All", "", [
            N("Headcount", "'Data - Employees'.FTE[SUM: 'Data - Employees'.Role]"),
            N("Leavers", "IF 'Data - Employees'.Leaver This Month? THEN 1 ELSE 0", applies=("Employees",), notes="Should be in Data - Employees. Moved here for the dashboard."),
            N("Leavers by Role", "Leavers[SUM: 'Data - Employees'.Role]"),
            P("Attrition %", "Leavers by Role / Headcount", summary="FORMULA"),
            P("Annualised Attrition", "MOVINGSUM(Leavers by Role, -11, 0) / Headcount", summary="FORMULA"),
        ]),
        Mod("Reports - Headcount", "Reports", ("Departments",), "Month", "All", "", [
            N("FTE", "'Calcs - Headcount by CC'.FTE[SUM: 'Data - Cost Centre Map'.Department]"),
            N("Total Cost", "'Calcs - Headcount by CC'.Total Cost[SUM: 'Data - Cost Centre Map'.Department]"),
            N("Cost per FTE", "DIVIDE(Total Cost, FTE)", summary="FORMULA"),
            N("FTE Budget", "FTE[SELECT: VERSIONS.Budget]"),
            N("FTE Variance", "FTE - FTE Budget"),
        ]),
        Mod("zz Archive - 2021 Cost", "Calcs", ("Roles",), "Month", "All", "Old cost calc from go-live. Kept for reference.", [
            N("Headcount", "'Data - Employees'.FTE[SUM: 'Data - Employees'.Role]"),
            N("Cost", "'Calcs - Cost'.Total Cost[SUM: 'Data - Employees'.Role]"),
            N("Cost per Head", "DIVIDE(Cost, Headcount)", summary="FORMULA"),
        ]),
    ]
    procs = {
        "Monthly Refresh": ("2026-09-04 08:15:31", 22400, ["Import Employees from Workday", "Import from Caldergate Data Hub - Cost Centre Map"]),
        "Push to FP&A": ("2026-09-05 09:10:44", 3600, ["Export Headcount Cost to FP&A"]),
    }
    acts = [
        Act("Import Employees from Workday", "import", "Data - Employees", "2026-09-04 08:15:31", 21900, ("Monthly Refresh",)),
        Act("Import from Caldergate Data Hub - Cost Centre Map", "import", "Data - Cost Centre Map", "2026-09-04 08:15:53", 500, ("Monthly Refresh",)),
        Act("Import from Caldergate FP&A - Assumptions", "import", "Inputs - Settings", "2022-08-17 13:48:10", 200, (), notes="Rates now keyed by hand."),
        Act("Export Headcount Cost to FP&A", "export", "Calcs - Headcount by CC", "2026-09-05 09:10:44", 3600, ("Push to FP&A",)),
        Act("Export Headcount by Department", "export", "Reports - Headcount", "2026-09-08 15:58:02", 400, ()),
        Act("Export Leavers Report", "export", "Calcs - Attrition", "2024-12-19 10:02:00", 300, ()),
    ]
    return ModelDef("3 Workforce Planning", mods, procs, acts, effort=False)


# ---------------------------------------------------------------- model 4: board reporting (2023, in-house)

def board() -> ModelDef:
    mods = [
        Mod("SYS01 Time", "System", (), "Month", "Not Applicable", "", [
            B("Current Period?", "ITEM(Time) = 'SYS00 Settings'.Current Period", summary="NONE"),
            T("Period Label", "NAME(ITEM(Time))", summary="NONE"),
        ]),
        Mod("SYS00 Settings", "System", (), "Not Applicable", "Not Applicable", "", [
            LI("Current Period", "TIME", summary="NONE"), T("Pack Title", summary="NONE"),
        ]),
        Mod("DAT01 P&L", "Data", ("Cost Centres",), "Month", "All", "From FP&A CAL07.", [
            N("Revenue"), N("COGS"), N("Opex"), N("Staff Cost"), N("EBITDA"), N("Depreciation"), N("EBIT"),
        ]),
        Mod("DAT02 Board Lines", "Data", (), "Month", "All", "From FP&A OUT02, summed to total.", [
            N("Revenue"), N("EBITDA"), N("Budget Revenue"), N("Revenue Variance"),
        ]),
        Mod("DAT03 Headcount", "Data", ("Departments",), "Month", "Not Applicable", "", [
            N("FTE"), N("Total Cost"),
        ]),
        Mod("CAL01 KPIs", "Calculation", (), "Month", "All", "", [
            N("FTE", "'DAT03 Headcount'.FTE"),
            N("Revenue per FTE", "'DAT02 Board Lines'.Revenue / FTE", summary="FORMULA"),
            P("Opex Ratio", "DIVIDE('DAT01 P&L'.Opex, 'DAT01 P&L'.Revenue)", summary="FORMULA"),
            N("Revenue Prior Year", "LAG('DAT02 Board Lines'.Revenue, 12, 0)"),
            P("Revenue Growth", "DIVIDE('DAT02 Board Lines'.Revenue - Revenue Prior Year, Revenue Prior Year)", summary="FORMULA"),
            P("EBITDA Margin", "DIVIDE('DAT02 Board Lines'.EBITDA, 'DAT02 Board Lines'.Revenue)", summary="FORMULA"),
            N("Revenue YTD", "YEARTODATE('DAT02 Board Lines'.Revenue)"),
        ]),
        Mod("OUT01 Board Dashboard", "Output", (), "Month", "All", "", [
            N("Revenue", "'DAT02 Board Lines'.Revenue"), N("EBITDA", "'DAT02 Board Lines'.EBITDA"),
            N("Revenue per FTE", "'CAL01 KPIs'.Revenue per FTE"), P("Revenue Growth", "'CAL01 KPIs'.Revenue Growth"),
            T("Commentary", summary="NONE"), T("Prepared By", summary="NONE"),
        ]),
    ]
    procs = {
        "Refresh Pack": ("2026-09-08 16:05:40", 4800, ["Import from Caldergate FP&A - P&L by Cost Centre", "Import from Caldergate FP&A - Board Pack", "Import from Workforce Planning - Headcount by Department"]),
    }
    acts = [
        Act("Import from Caldergate FP&A - P&L by Cost Centre", "import", "DAT01 P&L", "2026-09-08 16:05:40", 2600, ("Refresh Pack",)),
        Act("Import from Caldergate FP&A - Board Pack", "import", "DAT02 Board Lines", "2026-09-08 16:05:43", 900, ("Refresh Pack",)),
        Act("Import from Workforce Planning - Headcount by Department", "import", "DAT03 Headcount", "2026-09-08 16:05:44", 500, ("Refresh Pack",)),
        Act("Export Board Pack PDF Data", "export", "OUT01 Board Dashboard", "2026-09-08 16:07:12", 300, ()),
    ]
    return ModelDef("4 Board Reporting", mods, procs, acts)


# ---------------------------------------------------------------- writers

def cells(applies, ts, vers):
    n = 1
    for d in applies:
        n *= DIMS[d]
    return n * TIME[ts] * VERSIONS[vers]


def li_row(m: Mod, li: LI, refby: str, effort: str):
    applies = m.applies if li.applies is None else li.applies
    ts = li.ts or m.ts
    vers = li.vers or m.vers
    fmt = FMT.get(li.fmt, li.fmt)
    dtype = json.loads(fmt)["dataType"]
    if li.summary is None:
        summ = "SUM" if dtype == "NUMBER" else "NONE"
    else:
        summ = li.summary
    return {
        "": li.name, "Format": fmt, "Formula": li.formula, "Summary": SUMMARY[summ],
        "Applies To": ", ".join(applies) if applies else "-", "Time Scale": ts,
        "Time Range": "Model Calendar" if ts != "Not Applicable" else "Not Applicable", "Versions": vers,
        "Style": li.style, "Cell Count": str(cells(applies, ts, vers)), "Calculation Effort": effort, "Notes": li.notes,
        "Read Access Driver": "-", "Write Access Driver": "-", "Users List": "", "Parent": "", "Is Summary": "false",
        "Formula Scope": "All Versions" if vers == "All" else "-", "Code": "", "Use Switchover": "true" if vers == "All" and li.formula else "false",
        "Breakback": "false", "Brought-Forward": "false", "Start of Section": "false", "Data Tags": "-",
        "Referenced By": refby, "Module Name": m.name,
    }


def mod_header_row(m: Mod):
    total = sum(cells(m.applies if li.applies is None else li.applies, li.ts or m.ts, li.vers or m.vers) for li in m.items)
    return {"": m.name, "Applies To": ", ".join(m.applies) if m.applies else "", "Time Scale": m.ts,
            "Time Range": "Model Calendar" if m.ts != "Not Applicable" else "Not Applicable", "Versions": m.vers,
            "Cell Count": str(total), "Users List": "Show All Users: On", "Breakback": "New Line Items: Off"}


def write_csv(path, cols, rows):
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in cols})


def effort_weights(md: ModelDef, graph) -> dict:
    """Deterministic share of calculation effort per calculated line item:
    cells x (1 + references) x clause and IF multipliers, normalised to 100."""
    w = {}
    for m in md.modules:
        for li in m.items:
            if not li.formula:
                continue
            applies = m.applies if li.applies is None else li.applies
            c = cells(applies, li.ts or m.ts, li.vers or m.vers)
            refs = len(graph.edges.get((m.name, li.name), ()))
            f = li.formula.upper()
            mult = (3 if "[SUM" in f or "LOOKUP" in f else 1) * (1.6 if " IF " in f or f.startswith("IF ") else 1) * (2 if "MOVINGSUM" in f or "CUMULATE" in f else 1) * (4 if "FINDITEM" in f else 1)
            w[(m.name, li.name)] = c * (1 + refs) * mult
    tot = sum(w.values()) or 1
    return {k: f"{100 * v / tot:05.2f}%" for k, v in w.items()}


def write_model(md: ModelDef):
    folder = OUT / md.folder
    folder.mkdir(parents=True, exist_ok=True)
    li_path, mod_path, act_path = folder / "Line Items.csv", folder / "Modules.csv", folder / "Actions.csv"

    # pass 1: no Referenced By, so the tool's own graph can compute it
    rows = []
    for m in md.modules:
        rows.append(mod_header_row(m))
        rows += [li_row(m, li, "", "") for li in m.items]
    write_csv(li_path, LI_COLS, rows)
    model = load_model(li_path, name=md.folder)
    g = build_graph(model)
    if g.parse_errors:
        for k, e in g.parse_errors.items():
            print(f"  PARSE ERROR {k}: {e}")
        raise SystemExit(f"{md.folder}: {len(g.parse_errors)} formulas do not parse")
    unresolved = [(k, r.path) for k, rs in g.refs.items() for r in rs if r.kind == "unresolved"]
    for k, p in unresolved:
        print(f"  unresolved {k}: {'.'.join(p)}")

    def refby(key):
        users = sorted(g.rev.get(key, ()))
        return ", ".join(name if mod == key[0] else f"'{mod}'.{name}" for mod, name in users)

    eff = effort_weights(md, g) if md.effort else {}
    rows = []
    for m in md.modules:
        rows.append(mod_header_row(m))
        rows += [li_row(m, li, refby((m.name, li.name)), eff.get((m.name, li.name), "00.00%" if md.effort and li.formula else "")) for li in m.items]
    write_csv(li_path, LI_COLS, rows)

    # modules
    medges = g.module_edges()   # A uses B
    used_by = {}
    for a, bs in medges.items():
        for b in bs:
            used_by.setdefault(b, set()).add(a)
    mrows = []
    for m in md.modules:
        mrows.append({"": m.name, "Functional Area": m.fa, "Applies To": ", ".join(m.applies), "Time Scale": m.ts,
                      "Time Range": "Model Calendar" if m.ts != "Not Applicable" else "Not Applicable", "Versions": m.vers,
                      "Breakback": "New Line Items: Off", "Users List": "Show All Users: On", "Cell Count": mod_header_row(m)["Cell Count"],
                      "Notes": m.notes, "Read Access Driver": "", "Write Access Driver": "", "Data Tags": "", "Managed By": "",
                      "Referenced By": ", ".join(f"'{x}'" for x in sorted(used_by.get(m.name, ()))), "Used in Dashboards": "",
                      "Line Items": ", ".join(li.name for li in m.items)})
    write_csv(mod_path, MOD_COLS, mrows)

    # actions: sections Processes, Imports, Exports, Other Actions, then one section per process
    arows = [{"": "Processes"}]
    for p, (last, ms, steps) in md.processes.items():
        arows.append({"": p, "Start Date and Time (UTC)": last, "Most recent duration (ms)": str(ms)})
    for section, kind in (("Imports", "import"), ("Exports", "export"), ("Other Actions", "other")):
        arows.append({"": section})
        for a in md.actions:
            if a.kind != kind:
                continue
            detail = a.detail or (f"Import into '{a.target}'" if kind == "import" else f"Export from '{a.target}'" if kind == "export" else "")
            arows.append({"": a.name, "Action": detail, "Start Date and Time (UTC)": a.last, "Most recent duration (ms)": str(a.ms),
                          "Notes": a.notes, "Used in Processes": ", ".join(a.procs)})
    for p, (last, ms, steps) in md.processes.items():
        arows.append({"": p})
        arows += [{"": s} for s in steps]
    write_csv(act_path, ACT_COLS, arows)

    n_li = sum(len(m.items) for m in md.modules)
    print(f"{md.folder}: {len(md.modules)} modules, {n_li} line items, {len(g.parse_errors)} parse errors, {len(unresolved)} unresolved refs")


if __name__ == "__main__":
    for build in (data_hub, fpa, workforce, board):
        write_model(build())
    print(f"written to {OUT}")
