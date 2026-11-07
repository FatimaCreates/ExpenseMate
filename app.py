import streamlit as st
import matplotlib.pyplot as plt
from datetime import datetime

import database as db
import import_export as ie
from constants import SUPPORTED_CURRENCIES
from controllers import (
    TransactionController, BudgetController, UserController,
    CategoryController, SavingsController,
)

transaction_controller = TransactionController()
budget_controller = BudgetController()
user_controller = UserController()
category_controller = CategoryController()
savings_controller = SavingsController()

#versionfinalofcode

st.set_page_config(page_title="ExpenseMate", page_icon="🌿", layout="wide")

COLOR_BG = "#FFFFFF"
COLOR_CARD = "#F3F3F3"       # light grey cards
COLOR_INCOME = "#43A047"     # green
COLOR_EXPENSE = "#F57C00"    # orange
COLOR_TEXT = "#3D3D3D"       # dark grey text
COLOR_ALERT = "#E53935"      # red alert banner
COLOR_BORDER = "#E0E0E0"     # light grey border

db.init_db()

# CUSTOM CSS

st.markdown(f"""
<style>
    .stApp {{
        background-color: {COLOR_BG};
    }}
    .summary-card {{
        background-color: #FFFFFF;
        border: 1px solid {COLOR_BORDER};
        border-top: 4px solid var(--card-accent, {COLOR_INCOME});
        border-radius: 14px;
        padding: 18px 20px;
        text-align: left;
    }}
    .summary-card .card-top-row {{
        display: flex;
        align-items: center;
        gap: 8px;
    }}
    .summary-card h3 {{
        margin: 0;
        font-size: 14px;
        font-weight: 500;
        color: {COLOR_TEXT};
        opacity: 0.75;
    }}
    .summary-card p {{
        margin: 8px 0 0 0;
        font-size: 26px;
        font-weight: 700;
    }}
    /* --- Dark sidebar --- */
    section[data-testid="stSidebar"] {{
        background-color: #262B36;
    }}
    section[data-testid="stSidebar"] div[data-testid="stSidebarUserContent"] {{
        padding-top: 0rem;
    }}
    section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"] {{
        gap: 0.4rem;
    }}
    section[data-testid="stSidebar"] h1 {{
        margin-top: -1rem !important;
        padding-top: 0 !important;
        margin-bottom: 0.2rem !important;
    }}
    section[data-testid="stSidebar"] * {{
        color: #F0F0F0 !important;
    }}
    
    /* Sidebar dropdowns (e.g. Currency) sit on a white box, so the selected
       value and arrow must be black. The general sidebar rule above makes
       everything light, so we override just the <input> and the arrow button.
       (Newer Streamlit versions use data-testid="stSelectbox"; the
       data-baseweb lines keep older versions working too.) */
    section[data-testid="stSidebar"] [data-testid="stSelectbox"] input,
    section[data-testid="stSidebar"] div[data-baseweb="select"] input,
    section[data-testid="stSidebar"] div[data-baseweb="select"] div,
    section[data-testid="stSidebar"] div[data-baseweb="select"] span {{
        color: #000000 !important;
        -webkit-text-fill-color: #000000 !important;
        opacity: 1 !important;
    }}
    section[data-testid="stSidebar"] [data-testid="stSelectbox"] button,
    section[data-testid="stSidebar"] [data-testid="stSelectbox"] button svg,
    section[data-testid="stSidebar"] div[data-baseweb="select"] svg {{
        color: #000000 !important;
        fill: #000000 !important;
    }}
    section[data-testid="stSidebar"] [role="radiogroup"] label {{
        padding: 8px 12px;
        border-radius: 8px;
        margin-bottom: 2px;
    }}
    section[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) {{
        background-color: {COLOR_INCOME};
    }}
    section[data-testid="stSidebar"] div[data-testid="stButton"] button {{
        background-color: transparent !important;
        border: 1px solid #4A4F5A !important;
        border-radius: 8px !important;
        color: #F0F0F0 !important;
    }}
    .alert-banner {{
        background-color: {COLOR_ALERT};
        color: #FFFFFF;
        padding: 12px 16px;
        border-radius: 10px;
        margin-bottom: 10px;
        font-weight: 600;
    }}
    .auth-box {{
        background-color: {COLOR_CARD};
        border-radius: 16px;
        padding: 30px;
        max-width: 420px;
        margin: 40px auto;
    }}
    h1, h2, h3 {{
        color: {COLOR_TEXT};
    }}

    /* --- Custom styled table --- */
    .styled-table-wrapper {{
        overflow-x: auto;
        border-radius: 12px;
        border: 1px solid {COLOR_BORDER};
        margin-bottom: 10px;
    }}
    table.styled-table {{
        width: 100%;
        border-collapse: collapse;
        font-size: 14px;
        background-color: #FFFFFF;
    }}
    table.styled-table thead th {{
        background-color: {COLOR_INCOME};
        color: #FFFFFF;
        text-align: left;
        padding: 10px 14px;
        font-weight: 600;
        text-transform: uppercase;
        font-size: 12px;
        letter-spacing: 0.03em;
    }}
    table.styled-table tbody td {{
        padding: 10px 14px;
        color: {COLOR_TEXT};
        border-bottom: 1px solid {COLOR_BORDER};
    }}
    table.styled-table tbody tr:nth-child(even) {{
        background-color: #FAFAFA;
    }}
    table.styled-table tbody tr:hover {{
        background-color: #F0F0F0;
    }}
    .badge-income {{
        background-color: {COLOR_INCOME};
        color: white;
        padding: 3px 10px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
    }}
    .badge-expense {{
        background-color: {COLOR_EXPENSE};
        color: white;
        padding: 3px 10px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
    }}
    .amount-income {{
        color: {COLOR_INCOME};
        font-weight: 700;
    }}
    .amount-expense {{
        color: {COLOR_EXPENSE};
        font-weight: 700;
    }}

    /* --- Auth (Login/Register) screen --- */
    .block-container {{
        padding-top: 1rem;
    }}
    .auth-illustration-panel {{
        background: linear-gradient(160deg, #DCEFD8 0%, #FFF3E0 100%);
        border-radius: 24px;
        padding: 50px 36px;
        height: 480px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        text-align: center;
    }}
    .auth-illustration-panel h1 {{
        font-family: 'Georgia', serif;
        font-size: 34px;
        margin: 14px 0 4px 0;
        color: {COLOR_TEXT};
    }}
    .auth-illustration-panel p {{
        color: {COLOR_TEXT};
        opacity: 0.75;
        font-size: 15px;
        margin-bottom: 20px;
    }}
    .auth-toggle-row {{
        display: flex;
        background-color: {COLOR_CARD};
        border-radius: 999px;
        padding: 4px;
        margin-bottom: 24px;
    }}
    div[data-testid="stButton"] button[kind="primary"] {{
        background-color: {COLOR_INCOME} !important;
        color: white !important;
        border: none !important;
        border-radius: 999px !important;
        font-weight: 700 !important;
    }}
    div[data-testid="stButton"] button[kind="secondary"] {{
        background-color: transparent !important;
        color: {COLOR_TEXT} !important;
        border: 1px solid {COLOR_BORDER} !important;
        border-radius: 999px !important;
        font-weight: 600 !important;
    }}
    div[data-testid="stForm"] {{
        border: none;
        padding: 0;
    }}
    div[data-testid="stForm"] .stTextInput input {{
        border-radius: 10px;
        border: 1px solid {COLOR_BORDER};
        padding: 10px 14px;
    }}
    div[data-testid="stFormSubmitButton"] {{
        width: 100%;
        display: flex;
    }}
    div[data-testid="stFormSubmitButton"] button {{
        background: linear-gradient(90deg, {COLOR_EXPENSE}, #FFA94D) !important;
        color: white !important;
        border: none !important;
        border-radius: 999px !important;
        padding: 14px 28px !important;
        font-weight: 700 !important;
        font-size: 16px !important;
        line-height: 1.2 !important;
        width: 100% !important;
        min-width: 100% !important;
        min-height: 48px !important;
        white-space: nowrap !important;
        text-overflow: initial !important;
        overflow: visible !important;
        margin-top: 14px !important;
        box-shadow: 0 4px 12px rgba(245, 124, 0, 0.25) !important;
    }}
    div[data-testid="stFormSubmitButton"] button p {{
        font-size: 16px !important;
        font-weight: 700 !important;
        overflow: visible !important;
        white-space: nowrap !important;
    }}
</style>
""", unsafe_allow_html=True)


def render_transactions_table(transactions, show_id=False):
    """Build a themed HTML table for a list of transaction dicts."""
    if not transactions:
        return

    id_header = "<th>ID</th>" if show_id else ""
    rows_html = ""
    for t in transactions:
        id_cell = f"<td>{t['id']}</td>" if show_id else ""
        badge_class = "badge-income" if t["type"] == "income" else "badge-expense"
        amount_class = "amount-income" if t["type"] == "income" else "amount-expense"
        sign = "+" if t["type"] == "income" else "-"
        # NOTE: no leading whitespace on these lines — avoids Streamlit/Markdown
        # treating indented HTML as a fenced code block once multiple rows exist.
        rows_html += (
            "<tr>"
            f"{id_cell}"
            f"<td>{t['date']}</td>"
            f'<td><span class="{badge_class}">{t["type"].capitalize()}</span></td>'
            f"<td>{t['category']}</td>"
            f'<td class="{amount_class}">{sign} {CURRENCY_SYMBOL} {t["amount"]:,.0f}</td>'
            f"<td>{t.get('note') or '—'}</td>"
            "</tr>"
        )

    html = (
        '<div class="styled-table-wrapper">'
        '<table class="styled-table">'
        "<thead><tr>"
        f"{id_header}"
        "<th>Date</th><th>Type</th><th>Category</th><th>Amount</th><th>Note</th>"
        "</tr></thead>"
        f"<tbody>{rows_html}</tbody>"
        "</table>"
        "</div>"
    )
    st.markdown(html, unsafe_allow_html=True)


def render_simple_table(rows, columns):
    """Build a themed HTML table for simple list-of-dict data (e.g. budgets)."""
    if not rows:
        return

    header_html = "".join(f"<th>{label}</th>" for _, label in columns)
    rows_html = ""
    for r in rows:
        cells = "".join(f"<td>{r[key]}</td>" for key, _ in columns)
        rows_html += f"<tr>{cells}</tr>"

    html = (
        '<div class="styled-table-wrapper">'
        '<table class="styled-table">'
        f"<thead><tr>{header_html}</tr></thead>"
        f"<tbody>{rows_html}</tbody>"
        "</table>"
        "</div>"
    )
    st.markdown(html, unsafe_allow_html=True)


# SESSION STATE

if "user" not in st.session_state:
    st.session_state["user"] = None


def login_screen():
    if "auth_mode" not in st.session_state:
        st.session_state["auth_mode"] = "login"

    left_col, right_col = st.columns([1, 1.1], gap="large")

    with left_col:
        illustration_svg = (
            '<svg width="140" height="140" viewBox="0 0 140 140" xmlns="http://www.w3.org/2000/svg">'
            '<circle cx="70" cy="70" r="60" fill="#43A047" opacity="0.12"/>'
            '<rect x="40" y="70" width="14" height="35" rx="3" fill="#43A047"/>'
            '<rect x="60" y="55" width="14" height="50" rx="3" fill="#81C784"/>'
            '<rect x="80" y="40" width="14" height="65" rx="3" fill="#F57C00"/>'
            '<circle cx="95" cy="35" r="18" fill="#FFFFFF" stroke="#F57C00" stroke-width="3"/>'
            '<text x="95" y="41" font-size="16" text-anchor="middle" fill="#F57C00">$</text>'
            '<path d="M30 108 Q70 95 105 60" stroke="#43A047" stroke-width="3" fill="none" stroke-dasharray="5,5"/>'
            '</svg>'
        )

        panel_html = (
            '<div class="auth-illustration-panel">'
            + illustration_svg +
            '<h1>🌿 ExpenseMate</h1>'
            '<p>Plan today. Save smart.<br>Build tomorrow.</p>'
            '</div>'
        )

        st.markdown(panel_html, unsafe_allow_html=True)

    with right_col:
        st.write("")
        st.write("")

        toggle_col1, toggle_col2 = st.columns(2)
        with toggle_col1:
            if st.button("Login", key="btn_login_toggle", use_container_width=True,
                         type="primary" if st.session_state["auth_mode"] == "login" else "secondary"):
                st.session_state["auth_mode"] = "login"
                st.rerun()
        with toggle_col2:
            if st.button("Register", key="btn_register_toggle", use_container_width=True,
                         type="primary" if st.session_state["auth_mode"] == "register" else "secondary"):
                st.session_state["auth_mode"] = "register"
                st.rerun()

        st.write("")

        if st.session_state["auth_mode"] == "login":
            with st.form("login_form"):
                username = st.text_input("👤 Username")
                password = st.text_input("🔒 Password", type="password")
                submitted = st.form_submit_button("Login", use_container_width=True)

                if submitted:
                    result = user_controller.login(username, password)
                    if result.ok:
                        st.session_state["user"] = result.data
                        st.rerun()
                    else:
                        st.error(result.message)
        else:
            with st.form("register_form"):
                new_username = st.text_input("👤 Choose a Username")
                new_password = st.text_input("🔒 Choose a Password", type="password")
                confirm_password = st.text_input("🔒 Confirm Password", type="password")
                new_currency = st.selectbox(
                    "💱 Currency",
                    list(SUPPORTED_CURRENCIES.keys()),
                    format_func=lambda c: f"{c} ({SUPPORTED_CURRENCIES[c]})",
                )
                submitted = st.form_submit_button("Register", use_container_width=True)

                if submitted:
                    result = user_controller.register(
                        new_username, new_password, confirm_password, new_currency
                    )
                    if result.ok:
                        st.success(result.message)
                    else:
                        st.error(result.message)


if st.session_state["user"] is None:
    login_screen()
    st.stop()

user = st.session_state["user"]
user_id = user["id"]

# Multi-currency: each user has one display currency (no conversion).
CURRENCY_SYMBOL = SUPPORTED_CURRENCIES.get(user.get("currency", "PKR"), "Rs.")

category_controller.ensure_defaults(user_id)

# SIDEBAR: WELCOME + NAVIGATION (no profile picture)

st.sidebar.title("ExpenseMate 🌿")
st.sidebar.markdown(f"**Welcome, {user['username']}**")

if st.sidebar.button("Log out"):
    st.session_state["user"] = None
    st.rerun()

st.sidebar.markdown("---")
currency_codes = list(SUPPORTED_CURRENCIES.keys())
current_currency = user.get("currency", "PKR")
chosen_currency = st.sidebar.selectbox(
    "💱 Currency",
    currency_codes,
    index=currency_codes.index(current_currency) if current_currency in currency_codes else 0,
    format_func=lambda c: f"{c} ({SUPPORTED_CURRENCIES[c]})",
    key="currency_selector",
)
if chosen_currency != current_currency:
    user_controller.change_currency(user_id, chosen_currency)
    st.session_state["user"]["currency"] = chosen_currency
    st.rerun()

st.sidebar.markdown("---")
NAV_OPTIONS = ["🏠 Dashboard", "➕ Add Transaction", "💰 Budgets", "🎯 Savings Goals", "📤 Import / Export"]
page_full = st.sidebar.radio("Navigate", NAV_OPTIONS, key="nav_radio", label_visibility="collapsed")
page = page_full.split(" ", 1)[1]  # strip the icon prefix before comparing below

current_month = datetime.now().strftime("%Y-%m")


def go_to(target_page_name):
    """
    Used by empty-state CTA buttons to jump to another page (by plain name).

    IMPORTANT: this must be called as a button's `on_click` callback, NOT
    inside an `if st.button(...):` block. Callbacks run *before* the script
    reruns and widgets are re-instantiated, so it's safe to write to
    st.session_state["nav_radio"] here. If you called this after the radio
    widget had already been instantiated in the same run, Streamlit raises
    StreamlitWidgetAlreadyInstantiatedError. Also note there's no
    st.rerun() here — on_click callbacks trigger a rerun automatically.
    """
    match = next(opt for opt in NAV_OPTIONS if opt.endswith(target_page_name))
    st.session_state["nav_radio"] = match


def render_empty_state(icon, message, button_label, target_page_name, section_key):
    """A friendly empty-state box with an icon, message, and a CTA button."""
    st.markdown(f"""
        <div style="background-color:{COLOR_CARD}; border:1px dashed {COLOR_BORDER};
                    border-radius:14px; padding:24px; text-align:center;">
            <div style="font-size:28px; margin-bottom:6px;">{icon}</div>
            <div style="color:{COLOR_TEXT}; opacity:0.75; margin-bottom:14px;">{message}</div>
        </div>
    """, unsafe_allow_html=True)
    st.button(
        button_label,
        key=f"cta_{section_key}",
        type="primary",
        use_container_width=True,
        on_click=go_to,
        args=(target_page_name,),
    )

# ===========================================================================
# PAGE: DASHBOARD
# ===========================================================================
if page == "Dashboard":
    st.title("Dashboard")
    st.caption(f"Showing summary for {current_month}")

    # Monthly Budget Summary: one controller call (Controller -> Service -> Repository)
    report = budget_controller.monthly_summary(user_id, current_month).data
    alerts = report["alerts"]
    for a in alerts:
        st.markdown(
            f"""<div class="alert-banner">⚠️ You've gone over budget in
            <b>{a['category']}</b> — spent {a['spent']:.0f} of {a['limit']:.0f}
            (over by {a['over_by']:.0f})</div>""",
            unsafe_allow_html=True,
        )

    summary = report["summary"]
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"""<div class="summary-card" style="--card-accent:{COLOR_INCOME}">
            <div class="card-top-row"><span>💵</span><h3>Total Income</h3></div>
            <p style="color:{COLOR_INCOME}">{CURRENCY_SYMBOL} {summary['total_income']:,.0f}</p>
            </div>""", unsafe_allow_html=True)
    with col2:
        st.markdown(f"""<div class="summary-card" style="--card-accent:{COLOR_EXPENSE}">
            <div class="card-top-row"><span>🧾</span><h3>Total Expense</h3></div>
            <p style="color:{COLOR_EXPENSE}">{CURRENCY_SYMBOL} {summary['total_expense']:,.0f}</p>
            </div>""", unsafe_allow_html=True)
    with col3:
        st.markdown(f"""<div class="summary-card" style="--card-accent:{COLOR_TEXT}">
            <div class="card-top-row"><span>📈</span><h3>Net Balance</h3></div>
            <p style="color:{COLOR_TEXT}">{CURRENCY_SYMBOL} {summary['net_balance']:,.0f}</p>
            </div>""", unsafe_allow_html=True)

    st.write("")

    chart_col, budget_col = st.columns([1.2, 1])

    with chart_col:
        st.subheader("Spending by Category")
        cat_summary = report["category_totals"]
        if cat_summary:
            fig, ax = plt.subplots()
            fig.patch.set_facecolor(COLOR_BG)
            ax.pie(
                cat_summary.values(),
                labels=cat_summary.keys(),
                autopct="%1.0f%%",
                colors=["#F57C00", "#FFA94D", "#43A047", "#81C784", "#9E9E9E", "#FFB300"],
                textprops={"color": COLOR_TEXT},
            )
            st.pyplot(fig)
        else:
            render_empty_state("📊", "No expenses recorded yet this month.", "Add Transaction", "Add Transaction", "spending_chart")

    with budget_col:
        st.subheader("Budget Progress")
        progress = report["progress"]
        if progress:
            for p in progress:
                pct = min(p["percent"], 100) / 100
                st.write(f"**{p['category']}** — {p['spent']:.0f} / {p['limit']:.0f}")
                st.progress(pct)
        else:
            render_empty_state("💰", "No budgets set yet.", "Set a Budget", "Budgets", "budget_progress")

    st.write("")
    st.subheader("Savings Goals")
    goals = savings_controller.goals_progress(user_id).data
    if goals:
        for g in goals:
            st.write(f"**{g['name']}** — {CURRENCY_SYMBOL} {g['saved_amount']:,.0f} / {g['target_amount']:,.0f}")
            st.progress(g["percent"] / 100)
    else:
        render_empty_state("🎯", "No savings goals yet.", "Add First Goal", "Savings Goals", "savings_goals")

    st.write("")
    st.subheader("Recent Transactions")
    transactions = transaction_controller.list_transactions(user_id).data
    if transactions:
        render_transactions_table(transactions)
    else:
        render_empty_state("🧾", "No transactions yet. Add your first one!", "Add Transaction", "Add Transaction", "recent_transactions")

# ===========================================================================
# PAGE: ADD TRANSACTION
# ===========================================================================
elif page == "Add Transaction":
    st.title("Add Transaction")

    categories = category_controller.list_names(user_id).data

    with st.form("add_transaction_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            date = st.date_input("Date", value=datetime.now(), max_value=datetime.now())
            type_ = st.selectbox("Type", ["expense", "income"])
        with col2:
            category = st.selectbox("Category", categories)
            amount = st.number_input("Amount", min_value=0.0, step=50.0)

        note = st.text_input("Note (optional)")
        submitted = st.form_submit_button("Add Transaction")

        if submitted:
            result = transaction_controller.add_transaction(
                user_id, str(date), type_, category, amount, note
            )
            if result.ok:
                st.success(f"{type_.capitalize()} of {CURRENCY_SYMBOL} {amount:,.0f} added to {category}!")
            elif result.error == "budget_exceeded":
                blocked = result.data
                st.error(
                    f"🚫 Transaction not added: it would exceed your {blocked['category']} budget. "
                    f"Spent {CURRENCY_SYMBOL} {blocked['spent']:,.0f} + this "
                    f"{CURRENCY_SYMBOL} {blocked['amount']:,.0f} is over the limit of "
                    f"{CURRENCY_SYMBOL} {blocked['limit']:,.0f} "
                    f"(over by {CURRENCY_SYMBOL} {blocked['over_by']:,.0f}). "
                    f"Increase the budget on the Budgets page or lower the amount."
                )
            else:
                st.error(result.message)

    with st.expander("➕ Don't see your category? Add a new one"):
        new_cat_col1, new_cat_col2 = st.columns([3, 1])
        with new_cat_col1:
            new_category_name = st.text_input(
                "New category name", key="new_category_input", placeholder="e.g. Gym, Subscriptions"
            )
        with new_cat_col2:
            st.write("")
            st.write("")
            if st.button("Add Category", key="add_category_btn"):
                result = category_controller.add_category(user_id, new_category_name)
                if result.ok:
                    st.success(result.message)
                    st.rerun()
                else:
                    st.error(result.message)

    st.write("")
    st.subheader("All Transactions")
    transactions = transaction_controller.list_transactions(user_id).data
    if transactions:
        render_transactions_table(transactions, show_id=True)

        st.write("")
        del_id = st.number_input("Enter transaction ID to delete", min_value=0, step=1)
        if st.button("Delete Transaction"):
            if del_id > 0:
                transaction_controller.delete_transaction(int(del_id))
                st.success(f"Transaction #{del_id} deleted.")
                st.rerun()
    else:
        st.info("No transactions yet.")

# ===========================================================================
# PAGE: BUDGETS
# ===========================================================================
elif page == "Budgets":
    st.title("Budgets")

    categories = category_controller.list_names(user_id).data

    with st.form("set_budget_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            category = st.selectbox("Category", categories)
        with col2:
            limit = st.number_input("Monthly Limit", min_value=0.0, step=100.0)

        submitted = st.form_submit_button("Set Budget")
        if submitted:
            result = budget_controller.set_budget(user_id, category, limit)
            if result.ok:
                st.success(f"Budget for {category} set to {CURRENCY_SYMBOL} {limit:,.0f}/month.")
            else:
                st.error(result.message)

    st.write("")
    st.subheader("Current Budgets")
    budgets = budget_controller.list_budgets(user_id).data
    if budgets:
        render_simple_table(budgets, [("category", "Category"), ("monthly_limit", f"Monthly Limit ({CURRENCY_SYMBOL})")])
    else:
        st.info("No budgets set yet.")

# ===========================================================================
# PAGE: SAVINGS GOALS
# ===========================================================================
elif page == "Savings Goals":
    st.title("Savings Goals")

    with st.form("add_goal_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Goal Name", placeholder="e.g. Emergency Fund")
        with col2:
            target = st.number_input("Target Amount", min_value=0.0, step=500.0)

        submitted = st.form_submit_button("Add Goal")
        if submitted:
            result = savings_controller.add_goal(user_id, name, target)
            if result.ok:
                st.success(f"Savings goal '{name}' added!")
            else:
                st.error(result.message)

    st.write("")
    st.subheader("Update Progress")
    goals = savings_controller.list_goals(user_id).data
    if goals:
        goal_names = {f"{g['name']} (ID {g['id']})": g["id"] for g in goals}
        selected = st.selectbox("Select Goal", list(goal_names.keys()))
        new_amount = st.number_input("Amount Saved So Far", min_value=0.0, step=100.0)
        if st.button("Update Progress"):
            savings_controller.update_progress(goal_names[selected], new_amount)
            st.success("Progress updated!")
            st.rerun()

        st.write("")
        st.subheader("All Goals")
        for g in savings_controller.goals_progress(user_id).data:
            st.write(f"**{g['name']}** — {CURRENCY_SYMBOL} {g['saved_amount']:,.0f} / {g['target_amount']:,.0f}")
            st.progress(g["percent"] / 100)
    else:
        st.info("No savings goals yet.")

# ===========================================================================
# PAGE: IMPORT / EXPORT
# ===========================================================================
elif page == "Import / Export":
    st.title("Import / Export")

    st.subheader("Export Transactions")
    if st.button("Export to CSV"):
        filepath = f"expensemate_export_user{user_id}.csv"
        count = ie.export_transactions_to_csv(user_id, filepath)
        with open(filepath, "rb") as f:
            st.download_button(
                label=f"Download CSV ({count} transactions)",
                data=f,
                file_name="expensemate_export.csv",
                mime="text/csv",
            )

    st.write("")
    st.subheader("Import Transactions")
    uploaded_file = st.file_uploader("Choose a CSV file", type="csv")
    if uploaded_file is not None:
        temp_path = f"temp_import_user{user_id}.csv"
        with open(temp_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        result = ie.import_transactions_from_csv(user_id, temp_path)
        st.success(f"Imported {result['imported']} transactions.")
        if result["skipped"] > 0:
            st.warning(f"Skipped {result['skipped']} rows due to errors:")
            for err in result["errors"]:
                st.text(err)