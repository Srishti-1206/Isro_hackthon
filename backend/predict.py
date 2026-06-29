import pandas as pd
from prophet import Prophet

# Load the collected metrics
df = pd.read_csv("backend/metrics.csv")

# Prophet requires these column names
df = df.rename(columns={
    "timestamp": "ds",
    "cpu": "y"
})

# Convert timestamp to datetime
df["ds"] = pd.to_datetime(df["ds"])

# Create and train the model
model = Prophet(
    daily_seasonality=False,
    weekly_seasonality=False,
    yearly_seasonality=False
)

model.fit(df)

# Predict the next 20 readings (5 seconds apart)
future = model.make_future_dataframe(
    periods=20,
    freq="5s"
)

forecast = model.predict(future)



print("\n===== CPU PREDICTION =====\n")

current_cpu = df["y"].iloc[-1]
predicted_cpu = forecast["yhat"].iloc[-1]

print(f"Current CPU Usage      : {current_cpu:.2f}%")
print(f"Predicted CPU Usage    : {predicted_cpu:.2f}%")

change = predicted_cpu - current_cpu

if predicted_cpu >= 80:
    print("\n ALERT: High CPU usage predicted!")

elif change > 5:
    print("\n CPU usage is rising.")

else:
    print("\n System appears stable.")