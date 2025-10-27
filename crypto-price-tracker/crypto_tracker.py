import streamlit as st
import requests
import pandas as pd
import smtplib
import time
import json
import os
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import plotly.graph_objects as go
from plotly.subplots import make_subplots

class CryptoPriceTracker:
    def __init__(self):
        self.base_url = "https://api.coingecko.com/api/v3"
        self.alert_log_file = "price_alerts.log"
        self.setup_email_config()
    
    def setup_email_config(self):
        """Setup email configuration from environment variables or user input"""
        if 'email_config' not in st.session_state:
            st.session_state.email_config = {
                'smtp_server': os.getenv('SMTP_SERVER', ''),
                'smtp_port': int(os.getenv('SMTP_PORT', 587)),
                'email_address': os.getenv('EMAIL_ADDRESS', ''),
                'email_password': os.getenv('EMAIL_PASSWORD', '')
            }
    
    def get_crypto_list(self):
        """Fetch list of available cryptocurrencies"""
        try:
            url = f"{self.base_url}/coins/markets"
            params = {
                'vs_currency': 'usd',
                'order': 'market_cap_desc',
                'per_page': 100,
                'page': 1,
                'sparkline': False
            }
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            st.error(f"Error fetching crypto list: {e}")
            return []
    
    def get_price_data(self, crypto_ids):
        """Fetch current prices for selected cryptocurrencies"""
        try:
            if not crypto_ids:
                return {}
            
            crypto_ids_str = ','.join(crypto_ids)
            url = f"{self.base_url}/simple/price"
            params = {
                'ids': crypto_ids_str,
                'vs_currencies': 'usd',
                'include_24hr_change': 'true',
                'include_market_cap': 'true',
                'include_24hr_vol': 'true'
            }
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            st.error(f"Error fetching price data: {e}")
            return {}
    
    def get_historical_data(self, crypto_id, days=7):
        """Fetch historical price data for charts"""
        try:
            url = f"{self.base_url}/coins/{crypto_id}/market_chart"
            params = {
                'vs_currency': 'usd',
                'days': days,
                'interval': 'daily'
            }
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # Process historical data
            prices = data['prices']
            timestamps = [datetime.fromtimestamp(price[0]/1000) for price in prices]
            values = [price[1] for price in prices]
            
            return timestamps, values
        except Exception as e:
            st.error(f"Error fetching historical data for {crypto_id}: {e}")
            return [], []
    
    def send_email_alert(self, crypto_name, current_price, threshold_price, alert_type):
        """Send email alert when price threshold is met"""
        try:
            config = st.session_state.email_config
            
            if not all([config['smtp_server'], config['email_address'], config['email_password']]):
                st.warning("Email configuration incomplete. Please check your settings.")
                return False
            
            # Create message
            msg = MIMEMultipart()
            msg['From'] = config['email_address']
            msg['To'] = config['email_address']
            msg['Subject'] = f"Crypto Price Alert: {crypto_name}"
            
            body = f"""
            CRYPTO PRICE ALERT
            
            Cryptocurrency: {crypto_name}
            Current Price: ${current_price:,.2f}
            Alert Type: {alert_type}
            Threshold Price: ${threshold_price:,.2f}
            
            Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            
            This is an automated alert from your Crypto Price Tracker.
            """
            
            msg.attach(MIMEText(body, 'plain'))
            
            # Send email
            server = smtplib.SMTP(config['smtp_server'], config['smtp_port'])
            server.starttls()
            server.login(config['email_address'], config['email_password'])
            text = msg.as_string()
            server.sendmail(config['email_address'], config['email_address'], text)
            server.quit()
            
            return True
            
        except Exception as e:
            st.error(f"Error sending email alert: {e}")
            return False
    
    def log_alert(self, crypto_name, current_price, threshold_price, alert_type, email_sent):
        """Log price alerts to file"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'crypto': crypto_name,
            'current_price': current_price,
            'threshold_price': threshold_price,
            'alert_type': alert_type,
            'email_sent': email_sent
        }
        
        with open(self.alert_log_file, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')
    
    def check_alerts(self, price_data, alerts):
        """Check if any price alerts should be triggered"""
        triggered_alerts = []
        
        for alert in alerts:
            crypto_id = alert['crypto_id']
            crypto_name = alert['crypto_name']
            threshold = alert['threshold']
            alert_type = alert['type']
            
            if crypto_id in price_data:
                current_price = price_data[crypto_id]['usd']
                
                if (alert_type == 'above' and current_price >= threshold) or \
                   (alert_type == 'below' and current_price <= threshold):
                    
                    # Send email alert
                    email_sent = self.send_email_alert(
                        crypto_name, current_price, threshold, alert_type
                    )
                    
                    # Log alert
                    self.log_alert(
                        crypto_name, current_price, threshold, alert_type, email_sent
                    )
                    
                    triggered_alerts.append({
                        'crypto_name': crypto_name,
                        'current_price': current_price,
                        'threshold': threshold,
                        'type': alert_type,
                        'email_sent': email_sent
                    })
        
        return triggered_alerts

def main():
    st.set_page_config(
        page_title="Crypto Price Tracker",
        page_icon="₿",
        layout="wide"
    )
    
    st.title("🚀 Crypto Price Tracker")
    st.markdown("Track live cryptocurrency prices with customizable alerts")
    
    # Initialize tracker
    tracker = CryptoPriceTracker()
    
    # Sidebar for configuration
    st.sidebar.header("Configuration")
    
    # Email configuration
    st.sidebar.subheader("Email Alerts Setup")
    smtp_server = st.sidebar.text_input("SMTP Server", value=st.session_state.email_config['smtp_server'])
    smtp_port = st.sidebar.number_input("SMTP Port", value=st.session_state.email_config['smtp_port'])
    email_address = st.sidebar.text_input("Email Address", value=st.session_state.email_config['email_address'])
    email_password = st.sidebar.text_input("Email Password", type="password", value=st.session_state.email_config['email_password'])
    
    # Update email config
    st.session_state.email_config.update({
        'smtp_server': smtp_server,
        'smtp_port': smtp_port,
        'email_address': email_address,
        'email_password': email_password
    })
    
    # Auto-refresh settings
    st.sidebar.subheader("Auto-refresh")
    refresh_interval = st.sidebar.selectbox(
        "Refresh Interval (seconds)",
        [30, 60, 120, 300],
        index=1
    )
    
    # Initialize session state variables
    if 'alerts' not in st.session_state:
        st.session_state.alerts = []
    if 'selected_cryptos' not in st.session_state:
        st.session_state.selected_cryptos = []
    if 'last_refresh' not in st.session_state:
        st.session_state.last_refresh = datetime.now()
    
    # Main content area
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("📊 Live Crypto Prices")
        
        # Fetch available cryptocurrencies
        crypto_list = tracker.get_crypto_list()
        
        if crypto_list:
            # Crypto selection
            crypto_options = {f"{crypto['name']} ({crypto['symbol'].upper()})": crypto['id'] for crypto in crypto_list}
            selected_crypto_names = st.multiselect(
                "Select cryptocurrencies to track:",
                options=list(crypto_options.keys()),
                default=st.session_state.selected_cryptos
            )
            
            st.session_state.selected_cryptos = selected_crypto_names
            selected_crypto_ids = [crypto_options[name] for name in selected_crypto_names]
            
            if selected_crypto_ids:
                # Fetch and display price data
                price_data = tracker.get_price_data(selected_crypto_ids)
                
                if price_data:
                    # Create price table
                    price_table_data = []
                    for crypto_name, crypto_id in zip(selected_crypto_names, selected_crypto_ids):
                        if crypto_id in price_data:
                            data = price_data[crypto_id]
                            price_table_data.append({
                                'Cryptocurrency': crypto_name.split(' (')[0],
                                'Symbol': crypto_name.split(' (')[1].replace(')', ''),
                                'Price (USD)': f"${data['usd']:,.2f}",
                                '24h Change': f"{data['usd_24h_change']:.2f}%" if data.get('usd_24h_change') else 'N/A',
                                'Market Cap': f"${data['usd_market_cap']:,.0f}" if data.get('usd_market_cap') else 'N/A',
                                '24h Volume': f"${data['usd_24h_vol']:,.0f}" if data.get('usd_24h_vol') else 'N/A'
                            })
                    
                    # Display price table
                    df = pd.DataFrame(price_table_data)
                    st.dataframe(df, use_container_width=True)
                    
                    # Check for alerts
                    triggered_alerts = tracker.check_alerts(price_data, st.session_state.alerts)
                    
                    if triggered_alerts:
                        st.warning("🚨 Price Alerts Triggered!")
                        for alert in triggered_alerts:
                            st.error(
                                f"{alert['crypto_name']}: ${alert['current_price']:,.2f} "
                                f"({alert['type']} ${alert['threshold']:,.2f}) - "
                                f"Email {'sent' if alert['email_sent'] else 'failed'}"
                            )
                    
                    # Price charts
                    st.subheader("📈 Price Trends (7 Days)")
                    chart_days = st.selectbox("Chart Period", [7, 30, 90], index=0)
                    
                    # Create charts in columns
                    cols = st.columns(2)
                    for idx, (crypto_name, crypto_id) in enumerate(zip(selected_crypto_names, selected_crypto_ids)):
                        if crypto_id in price_data:
                            with cols[idx % 2]:
                                timestamps, prices = tracker.get_historical_data(crypto_id, chart_days)
                                if timestamps and prices:
                                    fig = go.Figure()
                                    fig.add_trace(go.Scatter(
                                        x=timestamps, 
                                        y=prices,
                                        mode='lines',
                                        name=crypto_name.split(' (')[0],
                                        line=dict(color='#00ff88', width=2)
                                    ))
                                    
                                    fig.update_layout(
                                        title=f"{crypto_name.split(' (')[0]} Price Trend",
                                        xaxis_title="Date",
                                        yaxis_title="Price (USD)",
                                        height=300,
                                        showlegend=False
                                    )
                                    
                                    st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("🔔 Set Price Alerts")
        
        if selected_crypto_names:
            # Alert configuration
            selected_crypto_for_alert = st.selectbox(
                "Select cryptocurrency for alert:",
                selected_crypto_names
            )
            
            alert_type = st.selectbox("Alert when price goes:", ["above", "below"])
            threshold_price = st.number_input("Threshold price (USD):", min_value=0.0, step=0.01)
            
            if st.button("Add Alert") and threshold_price > 0:
                crypto_id = crypto_options[selected_crypto_for_alert]
                new_alert = {
                    'crypto_id': crypto_id,
                    'crypto_name': selected_crypto_for_alert.split(' (')[0],
                    'type': alert_type,
                    'threshold': threshold_price
                }
                
                # Check if alert already exists
                if new_alert not in st.session_state.alerts:
                    st.session_state.alerts.append(new_alert)
                    st.success("Alert added successfully!")
                else:
                    st.warning("This alert already exists!")
        
        # Display current alerts
        st.subheader("Active Alerts")
        if st.session_state.alerts:
            for i, alert in enumerate(st.session_state.alerts):
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write(f"**{alert['crypto_name']}** - {alert['type']} ${alert['threshold']:,.2f}")
                with col2:
                    if st.button("Remove", key=f"remove_{i}"):
                        st.session_state.alerts.pop(i)
                        st.rerun()
        else:
            st.info("No active alerts")
    
    # Auto-refresh
    current_time = datetime.now()
    time_diff = (current_time - st.session_state.last_refresh).total_seconds()
    
    if time_diff >= refresh_interval:
        st.session_state.last_refresh = current_time
        st.rerun()
    
    # Display last refresh time
    st.sidebar.write(f"Last refresh: {st.session_state.last_refresh.strftime('%H:%M:%S')}")
    
    # Manual refresh button
    if st.sidebar.button("Refresh Now"):
        st.session_state.last_refresh = datetime.now()
        st.rerun()
    
    # Alert logs section
    st.sidebar.subheader("Alert Logs")
    if st.sidebar.button("View Alert Logs"):
        try:
            if os.path.exists(tracker.alert_log_file):
                with open(tracker.alert_log_file, 'r') as f:
                    logs = [json.loads(line) for line in f.readlines()[-10:]]  # Last 10 entries
                
                if logs:
                    st.sidebar.write("Recent Alerts:")
                    for log in reversed(logs):
                        st.sidebar.text(
                            f"{log['crypto']}: ${log['current_price']:.2f} "
                            f"({log['alert_type']} ${log['threshold_price']:.2f})"
                        )
                else:
                    st.sidebar.info("No alert logs yet")
            else:
                st.sidebar.info("No alert logs yet")
        except Exception as e:
            st.sidebar.error(f"Error reading logs: {e}")

if __name__ == "__main__":
    main()