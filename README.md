# Home Assistant - Manx Utilities Integration

Hey! 👋 I've created a custom component for Home Assistant that lets you track your electricity usage and costs from Manx Utilities. If you're living on the Isle of Man and want to keep an eye on your power consumption, this integration's got you covered!

## What does it do?

This integration grabs data from your Manx Utilities account and creates two sensors in Home Assistant:
- **Electricity Cost**: Shows you how much you're spending (in £) each hour
- **Electricity Usage**: Shows your power consumption (in kWh) each hour

The sensors update hourly, giving you a nice view of your usage patterns throughout the day.

## Before you start

You'll need:
1. A Manx Utilities account with online access
2. Your Resource IDs for both cost and energy (I'll show you how to get these)
3. Home Assistant installed and running

## Getting Your Resource IDs

The Resource IDs are unique to your account. You need two of them:
- One for cost tracking (shows how much you're spending)
- One for energy usage (shows how many kWh you're using)

When you login to your Manx Utilities account, check the network tab in your browser's developer tools (F12) and look for calls to the API with the names "readings". You'll see URLs containing resource IDs that look something like this:
- Cost: `a1b2c3d4-5e6f-7g8h-9i10-j11k12l13m14`
- Energy: `n15o16p17-q18r-s19t-u20v-w21x22y23z24`

Make a note of both - you'll need these for setup!

## Installation

1. Download the `manx_utilities` folder from this repo
2. Copy it into your Home Assistant `custom_components` directory
   ```
   custom_components/
     manx_utilities/
       __init__.py
       manifest.json
       const.py
       config_flow.py
       sensor.py
       api.py
   ```
3. Restart Home Assistant
4. Go to Settings → Devices & Services
5. Click "Add Integration" and search for "Manx Utilities"
6. Enter your:
   - Username (your Manx Utilities login)
   - Password
   - Cost Resource ID
   - Energy Resource ID

And that's it! You should now see two new sensors in your Home Assistant.

## Using the Integration

The sensors will show up as:
- `sensor.electricity_cost` (in £)
- `sensor.electricity_usage` (in kWh)

These are perfect for:
- Adding to your energy dashboard
- Setting up automations based on high usage
- Creating nice graphs of your usage patterns
- Tracking your monthly spending

## Troubleshooting

If things aren't working:

1. Check your credentials and resource IDs are correct
2. Enable debug logging by adding this to your `configuration.yaml`:
   ```yaml
   logger:
     default: info
     logs:
       custom_components.manx_utilities: debug
   ```
3. Check the logs in Developer Tools → Logs

## Questions or Issues?

Found a bug? Got a feature request? Open an issue on GitHub and I'll take a look! 

## Credits

This integration was created by Quigg with inspiration from many other awesome Home Assistant custom components out there. Big thanks to the Home Assistant community for all the help and guidance!

Hope you find this useful! 🚀
