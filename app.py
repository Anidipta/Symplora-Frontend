import streamlit as st
import requests
import pandas as pd
from datetime import date
import time
import os
import plotly.express as px
import plotly.graph_objects as go
from utils import LeaveManagementUtils

from dotenv import load_dotenv
load_dotenv()

# Configure Streamlit page
st.set_page_config(
    page_title="Leave Management System",
    page_icon="🏖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# API base URL
API_BASE_URL = st.secrets.get("API_BASE_URL", os.getenv("API_BASE_URL", "http://127.0.0.1:5000"))


def make_api_call(method, endpoint, data=None):
    # Helper function for API calls with error handling
    try:
        url = f"{API_BASE_URL}{endpoint}"
        
        if method.upper() == 'GET':
            response = requests.get(url, timeout=10)
        elif method.upper() == 'POST':
            response = requests.post(url, json=data, timeout=10)
        elif method.upper() == 'PUT':
            response = requests.put(url, json=data, timeout=10)
        else:
            return {"success": False, "error": "Unsupported HTTP method"}
        
        return response.json()
    
    except requests.exceptions.ConnectionError:
        return {"success": False, "error": "Cannot connect to API server. Please ensure Flask app is running."}
    except requests.exceptions.Timeout:
        return {"success": False, "error": "Request timeout. Please try again."}
    except requests.exceptions.RequestException as e:
        return {"success": False, "error": f"Request failed: {str(e)}"}
    except ValueError:
        return {"success": False, "error": "Invalid response from server"}

def show_sidebar():
    # Sidebar navigation with styling
    st.sidebar.title("🏢 Leave Management")
    st.sidebar.markdown("---")
    
    menu_items = {
        "🏠 Dashboard": "dashboard",
        "👥 Employees": "employees", 
        "📝 Apply Leave": "apply_leave",
        "✅ Approve/Reject": "approve_reject",
        "📊 Leave Balance": "balance",
        "📈 Reports": "reports"
    }
    
    selected = st.sidebar.selectbox("Navigate to:", list(menu_items.keys()))
    return menu_items[selected]

def show_dashboard():
    st.title("📊 Dashboard")
    
    # Fetch dashboard stats
    stats_response = make_api_call("GET", "/dashboard/stats")
    
    if not stats_response.get("success"):
        st.error("Failed to load dashboard statistics")
        return
    
    stats = stats_response.get("stats", {})
    
    # Department Analytics Section
    st.subheader("Department Analytics")
    if stats.get("department_analytics"):
        dept_df = pd.DataFrame(stats["department_analytics"])
        
        # Department summary table
        st.dataframe(
            dept_df[[
                'department', 
                'total_employees', 
                'employees_on_leave', 
                'total_leaves', 
                'approved_rate'
            ]].rename(columns={
                'department': 'Department',
                'total_employees': 'Total Employees',
                'employees_on_leave': 'On Leave',
                'total_leaves': 'Total Leaves',
                'approved_rate': 'Approval Rate (%)'
            }),
            use_container_width=True
        )

    # Key metrics in columns with safe access using .get()
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Employees", stats.get("total_employees", 0))
    
    with col2:
        st.metric("Pending Requests", stats.get("pending_count", 0))
    
    with col3:
        st.metric("Approved This Month", stats.get("approved_this_month", 0))
    
    with col4:
        # Calculate approval rate with safe values
        total_requests = stats.get("pending_count", 0) + stats.get("approved_this_month", 0)
        approval_rate = (stats.get("approved_this_month", 0) / max(total_requests, 1)) * 100
        st.metric("Approval Rate", f"{approval_rate:.1f}%")
    
    st.markdown("---")
    
    # Charts section
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Leave Type Distribution")
        if stats.get("leave_type_distribution"):
            df_leave_types = pd.DataFrame(stats["leave_type_distribution"])
            fig_pie = px.pie(df_leave_types, values='count', names='leave_type', 
                           title="Leave Requests by Type (Current Year)")
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("No leave data available for current year")
    
    with col2:
        st.subheader("Recent Activity")
        # Fetch recent leave requests
        recent_response = make_api_call("GET", "/leave-requests?limit=5")
        if recent_response.get("success"):
            recent_requests = recent_response.get("requests", [])[:5]  # Get first 5 with safe access
            if recent_requests:
                for req in recent_requests:
                    status_color = {"pending": "🟡", "approved": "🟢", "rejected": "🔴"}.get(req["status"], "⚪")
                    st.write(f"{status_color} {req['employee_name']} - {req['leave_type'].title()} ({req['status']})")
            else:
                st.info("No recent leave requests")
        else:
            st.error("Failed to load recent activity")

def show_employees():
    st.title("👥 Employee Management")
    
    tab1, tab2 = st.tabs(["All Employees", "Add Employee"])
    
    with tab1:
        # Fetch and display existing employees
        response = leave_utils.api.get_employees()
        if response.get("success"):
            employees = response["employees"]
            if employees:
                df = pd.DataFrame(employees)
                df = df[["id", "name", "email", "department", "joining_date"]]
                df.columns = ["ID", "Name", "Email", "Department", "Joining Date"]
                st.dataframe(df, use_container_width=True)
            else:
                st.info("No employees found")
        else:
            st.error("Failed to load employees")
    
    with tab2:
        st.subheader("Add New Employee")
        
        with st.form("add_employee_form", clear_on_submit=True):
            name = st.text_input("Full Name*", key="emp_name")
            
            col1, col2 = st.columns(2)
            with col1:
                email = st.text_input("Email Address*", key="emp_email")
            with col2:
                department = st.selectbox(
                    "Department*",
                    options=["Engineering", "HR", "Finance", "Marketing", "Operations", "Sales"],
                    key="emp_dept"
                )
            
            joining_date = st.date_input(
                "Joining Date*",
                value=date.today(),
                min_value=date(2020, 1, 1),
                max_value=date.today(),
                key="emp_join_date"
            )
            
            submitted = st.form_submit_button("Add Employee", use_container_width=True)
            
            if submitted:
                if not name or not email or not department:
                    st.error("Please fill all required fields")
                    return
                
                # Validate data
                validation = leave_utils.validate_employee_data(
                    name=name,
                    email=email,
                    department=department,
                    joining_date=joining_date
                )
                
                if not validation["valid"]:
                    for error in validation["errors"]:
                        st.error(error)
                    return
                
                # Add employee
                result = leave_utils.api.add_employee(
                    name=name,
                    email=email,
                    department=department,
                    joining_date=joining_date
                )
                
                if result.get("success"):
                    st.success("Employee added successfully!")
                    time.sleep(1)  # Give user time to see the success message
                    st.rerun()  # Refresh the page to show updated employee list
                else:
                    st.error(f"Failed to add employee: {result.get('error', 'Unknown error')}")

def show_apply_leave():
    # Leave application interface
    st.title("📝 Apply for Leave")
    
    # Get employees for dropdown
    employees_response = make_api_call("GET", "/employees")
    
    if not employees_response.get("success"):
        st.error(f"Failed to load employees: {employees_response.get('error', 'Unknown error')}")
        return
    
    employees = employees_response["employees"]
    
    if not employees:
        st.warning("No employees found. Please add employees first.")
        return
    
    # Create employee options
    employee_options = {f"{emp['name']} ({emp['email']})": emp['id'] for emp in employees}
    
    with st.form("apply_leave_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            selected_employee = st.selectbox("Select Employee *", list(employee_options.keys()))
            leave_type = st.selectbox("Leave Type *", 
                                    ["annual", "sick", "emergency", "maternity", "paternity"])
            
        with col2:
            start_date = st.date_input("Start Date *", min_value=date.today())
            end_date = st.date_input("End Date *", min_value=date.today())
        
        reason = st.text_area("Reason", placeholder="Optional: Provide reason for leave")
        
        submitted = st.form_submit_button("Submit Leave Request", type="primary")
        
        if submitted:
            employee_id = employee_options[selected_employee]
            
            # Validation
            if start_date > end_date:
                st.error("Start date cannot be after end date")
            elif start_date < date.today():
                st.error("Cannot apply for leave on past dates")
            else:
                # API call to apply leave
                leave_data = {
                    "employee_id": employee_id,
                    "leave_type": leave_type,
                    "start_date": start_date.strftime('%Y-%m-%d'),
                    "end_date": end_date.strftime('%Y-%m-%d'),
                    "reason": reason.strip()
                }
                
                response = make_api_call("POST", "/leave-requests", leave_data)
                
                if response.get("success"):
                    st.success(f"✅ Leave request submitted successfully! Days requested: {response.get('days_requested', 'N/A')}")
                    st.rerun()
                else:
                    st.error(f"❌ Failed to submit leave request: {response.get('error', 'Unknown error')}")
    
    # Show recent leave requests
    st.markdown("---")
    st.subheader("Recent Leave Requests")
    
    requests_response = make_api_call("GET", "/leave-requests")
    
    if requests_response.get("success"):
        requests = requests_response["requests"][:10]  # Show latest 10
        
        if requests:
            df_requests = pd.DataFrame(requests)
            df_requests = df_requests[['employee_name', 'leave_type', 'start_date', 'end_date', 'days_requested', 'status', 'created_at']]
            
            # Format dates
            df_requests['start_date'] = pd.to_datetime(df_requests['start_date']).dt.strftime('%Y-%m-%d')
            df_requests['end_date'] = pd.to_datetime(df_requests['end_date']).dt.strftime('%Y-%m-%d')
            df_requests['created_at'] = pd.to_datetime(df_requests['created_at']).dt.strftime('%Y-%m-%d %H:%M')
            
            st.dataframe(df_requests, use_container_width=True, hide_index=True)
        else:
            st.info("No leave requests found")

def show_approve_reject():
    # Leave approval interface
    st.title("✅ Approve/Reject Leave Requests")
    
    # Get employees for approver selection
    employees_response = make_api_call("GET", "/employees")
    if not employees_response.get("success"):
        st.error("Failed to load employees")
        return
    
    employees = employees_response["employees"]
    approver_options = {f"{emp['name']} ({emp['email']})": emp['id'] for emp in employees}
    
    # Select approver
    selected_approver = st.selectbox("Select Approver *", list(approver_options.keys()))
    approver_id = approver_options[selected_approver]
    
    st.markdown("---")
    
    # Filter options
    col1, col2 = st.columns(2)
    with col1:
        status_filter = st.selectbox("Filter by Status", ["All", "pending", "approved", "rejected"])
    with col2:
        employee_filter = st.selectbox("Filter by Employee", ["All"] + list(approver_options.keys()))
    
    # Get leave requests
    params = ""
    if status_filter != "All":
        params += f"?status={status_filter}"
    if employee_filter != "All":
        employee_id = approver_options[employee_filter]
        params += f"{'&' if params else '?'}employee_id={employee_id}"
    
    requests_response = make_api_call("GET", f"/leave-requests{params}")
    
    if not requests_response.get("success"):
        st.error(f"Failed to load requests: {requests_response.get('error', 'Unknown error')}")
        return
    
    requests = requests_response["requests"]
    
    if not requests:
        st.info("No leave requests found matching the criteria")
        return
    
    # Display requests with action buttons
    for request in requests:
        with st.expander(f"{request['employee_name']} - {request['leave_type'].title()} Leave ({request['status'].upper()})"):
            col1, col2, col3 = st.columns([2, 1, 1])
            
            with col1:
                st.write(f"**Employee:** {request['employee_name']} ({request['department']})")
                st.write(f"**Period:** {request['start_date']} to {request['end_date']}")
                st.write(f"**Days:** {request['days_requested']}")
                st.write(f"**Reason:** {request['reason'] or 'Not provided'}")
                st.write(f"**Applied on:** {request['created_at']}")
                if request['status'] != 'pending':
                    st.write(f"**{request['status'].title()} by:** {request.get('approved_by_name', 'Unknown')}")
                    if request.get('approved_at'):
                        st.write(f"**{request['status'].title()} on:** {request['approved_at']}")
            
            with col2:
                if request['status'] == 'pending':
                    if st.button(f"✅ Approve", key=f"approve_{request['id']}"):
                        approve_response = make_api_call("PUT", f"/leave-requests/{request['id']}/approve", 
                                                       {"approved_by": approver_id})
                        
                        if approve_response.get("success"):
                            st.success("Leave request approved!")
                            st.rerun()
                        else:
                            st.error(f"Failed to approve: {approve_response.get('error', 'Unknown error')}")
            
            with col3:
                if request['status'] == 'pending':
                    if st.button(f"❌ Reject", key=f"reject_{request['id']}"):
                        reject_response = make_api_call("PUT", f"/leave-requests/{request['id']}/reject", 
                                                      {"approved_by": approver_id})
                        
                        if reject_response.get("success"):
                            st.success("Leave request rejected!")
                            st.rerun()
                        else:
                            st.error(f"Failed to reject: {reject_response.get('error', 'Unknown error')}")

def show_balance():
    # Leave balance interface
    st.title("📊 Leave Balance")
    
    # Get employees
    employees_response = make_api_call("GET", "/employees")
    
    if not employees_response.get("success"):
        st.error("Failed to load employees")
        return
    
    employees = employees_response["employees"]
    employee_options = {f"{emp['name']} ({emp['email']})": emp['id'] for emp in employees}
    
    # Select employee
    selected_employee = st.selectbox("Select Employee", list(employee_options.keys()))
    employee_id = employee_options[selected_employee]
    
    # Get balance information
    balance_response = make_api_call("GET", f"/employees/{employee_id}/balance")
    
    if not balance_response.get("success"):
        st.error(f"Failed to load balance: {balance_response.get('error', 'Unknown error')}")
        return
    
    employee_data = balance_response["employee"]
    balances = balance_response["balances"]
    
    # Display employee info
    st.subheader(f"Leave Balance for {employee_data['name']}")
    
    col1, col2 = st.columns(2)
    with col1:
        st.write(f"**Department:** {employee_data['department']}")
        st.write(f"**Email:** {employee_data['email']}")
    with col2:
        st.write(f"**Joining Date:** {employee_data['joining_date']}")
        st.write(f"**Employee ID:** {employee_data['id']}")
    
    st.markdown("---")
    
    # Balance cards
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🏖️ Annual Leave")
        annual = balances["annual_leave"]
        
        progress_value = annual["available"] / annual["total"] if annual["total"] > 0 else 0
        st.progress(progress_value)
        
        st.metric("Available", annual["available"], help=f"Total: {annual['total']}")
        st.write(f"**Used this year:** {annual['used']}")
        st.write(f"**Pending requests:** {annual['pending']}")
    
    with col2:
        st.subheader("🤒 Sick Leave")
        sick = balances["sick_leave"]
        
        progress_value = sick["available"] / sick["total"] if sick["total"] > 0 else 0
        st.progress(progress_value)
        
        st.metric("Available", sick["available"], help=f"Total: {sick['total']}")
        st.write(f"**Used this year:** {sick['used']}")
        st.write(f"**Pending requests:** {sick['pending']}")
    
    # Balance visualization
    st.markdown("---")
    st.subheader("Balance Overview")
    
    # Create balance chart
    balance_data = {
        'Leave Type': ['Annual Leave', 'Sick Leave'],
        'Available': [annual["available"], sick["available"]],
        'Used': [annual["used"], sick["used"]],
        'Pending': [annual["pending"], sick["pending"]]
    }
    
    df_balance = pd.DataFrame(balance_data)
    
    fig = go.Figure()
    fig.add_trace(go.Bar(name='Available', x=df_balance['Leave Type'], y=df_balance['Available'], marker_color='green'))
    fig.add_trace(go.Bar(name='Used', x=df_balance['Leave Type'], y=df_balance['Used'], marker_color='red'))
    fig.add_trace(go.Bar(name='Pending', x=df_balance['Leave Type'], y=df_balance['Pending'], marker_color='orange'))
    
    fig.update_layout(barmode='stack', title='Leave Balance Breakdown')
    st.plotly_chart(fig, use_container_width=True)

def show_reports():
    st.title("📈 Reports & Analytics")
    
    # Fetch stats
    stats_response = make_api_call("GET", "/dashboard/stats")
    
    if not stats_response.get("success"):
        st.error("Failed to load analytics data")
        return
    
    stats = stats_response.get("stats", {})
    dept_analytics = stats.get("department_analytics", [])
    
    if not dept_analytics:
        st.info("No analytics data available")
        return
    
    # Convert to DataFrame for analysis
    df = pd.DataFrame(dept_analytics)
    
    # Department-wise analysis
    st.subheader("Department Analysis")
    col1, col2 = st.columns(2)
    
    with col1:
        # Leave distribution pie chart
        fig1 = px.pie(
            df,
            values='total_employees',
            names='department',
            title='Employee Distribution by Department'
        )
        st.plotly_chart(fig1, use_container_width=True)
    
    with col2:
        # Approval rate bar chart
        fig2 = px.bar(
            df,
            x='department',
            y='approved_rate',
            title='Leave Approval Rate by Department',
            labels={'approved_rate': 'Approval Rate (%)', 'department': 'Department'}
        )
        st.plotly_chart(fig2, use_container_width=True)
    
    # Detailed metrics table
    st.subheader("Detailed Department Metrics")
    metrics_df = df[[
        'department',
        'total_employees',
        'employees_on_leave',
        'total_leaves',
        'approved_rate'
    ]].rename(columns={
        'department': 'Department',
        'total_employees': 'Total Employees',
        'employees_on_leave': 'Employees on Leave',
        'total_leaves': 'Total Leaves',
        'approved_rate': 'Approval Rate (%)'
    })
    st.dataframe(metrics_df, use_container_width=True)

# Initialize utils
leave_utils = LeaveManagementUtils()

def main():
    # Main application logic
    try:
        # Check API connectivity
        health_response = make_api_call("GET", "/health")
        if not health_response.get("status") == "healthy":
            st.error("🚨 API server is not responding. Please start the Flask application first.")
            st.stop()
        
        # Show sidebar and get selected page
        selected_page = show_sidebar()
        
        # Route to appropriate page
        if selected_page == "dashboard":
            show_dashboard()
        elif selected_page == "employees":
            show_employees()
        elif selected_page == "apply_leave":
            show_apply_leave()
        elif selected_page == "approve_reject":
            show_approve_reject()
        elif selected_page == "balance":
            show_balance()
        elif selected_page == "reports":
            show_reports()
        
        # Footer
        st.sidebar.markdown("---")
        st.sidebar.markdown("💻 **Leave Management System v1.0**")
        st.sidebar.markdown("Built with Streamlit & Flask")
    
    except Exception as e:
        st.error(f"Application error: {str(e)}")
        st.info("Please refresh the page or check the console for detailed error logs.")

if __name__ == "__main__":
    main()
