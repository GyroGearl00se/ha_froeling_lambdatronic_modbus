# Froeling Lambdatronic Modbus
Home Assistant integration for Fröling Lambdatronic heating systems via Modbus (currently supports Modbus TCP only).

## :warning: Disclaimer :warning:
> **This integration is experimental and has not been tested over long periods.**  
> It may contain missing or incorrect sensor data.  
> Feel free to open an [issue](https://github.com/your-repo/issues) or contribute via a [pull request](https://github.com/your-repo/pulls).

---

## :rocket: Features
With this integration, you can:
- Read real-time sensor data from your Fröling heating system.
- Monitor boiler performance and operational parameters.
- Configure heating system settings directly from Home Assistant.

---

## :computer: Requirements
To communicate with the heating system, you need a Modbus-to-TCP device.  
This integration has been tested with the **Waveshare RS232/RS485 to Ethernet Converter**, but other Serial-to-Ethernet adapters should work.

### :wrench: Enabling Modbus RTU on the Boiler
To enable Modbus RTU on your Fröling boiler:

1. Navigate to **Boiler Settings**.
2. Click the user icon and enter code `-7`.
3. Adjust the following settings:  
    - **Settings > General Settings > MODBUS Settings > Modbus Protokoll RTU** → `Set to 1`  
    - **Settings > General Settings > MODBUS Settings > Use Modbus Protokoll 2014** → `Yes`  
    - **Settings > General Settings > MODBUS Settings > Use COM2 as MODBUS Interface** → `Yes`  

---

## :hammer_and_wrench: Hardware Setup
I used a [Waveshare RS232/RS485 to Ethernet Converter](https://www.waveshare.com/rs232-485-to-eth.htm) and connected **RS232 to COM2** on the boiler.

![Waveshare configuration](docs/image.png)

Other Serial-to-Ethernet converters should work as well.

---

## :package: Installation
1. Copy the integration files into your Home Assistant `custom_components` folder.
2. Restart Home Assistant.
3. Add the integration via the Home Assistant UI.

---

## :orange_heart: Contributing
Contributions are welcome!  

1. **[Fork this repository](https://docs.github.com/en/get-started/quickstart/fork-a-repo).**  
2. Make changes within your fork.  
3. **[Create a pull request](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/creating-a-pull-request).**  

I’ll do my best to review and merge contributions.