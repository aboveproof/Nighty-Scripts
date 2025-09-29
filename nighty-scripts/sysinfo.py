import platform
import psutil
import socket
import subprocess
import json
import time
from datetime import datetime, timedelta
from pathlib import Path

def script_function():    
    CACHE_DURATION = 300  # 5 minutes
    cache_data = {}
    cache_timestamp = {}
    
    def get_cached_or_fetch(key, fetch_function):
        """Get data from cache if valid, otherwise fetch and cache it."""
        current_time = time.time()
        if (key in cache_data and 
            key in cache_timestamp and 
            current_time - cache_timestamp[key] < CACHE_DURATION):
            return cache_data[key]
        
        try:
            data = fetch_function()
            cache_data[key] = data
            cache_timestamp[key] = current_time
            return data
        except Exception as e:
            print(f"Error fetching {key}: {e}", type_="ERROR")
            return cache_data.get(key, "N/A")
    
    def clear_cache():
        """Clear all cached system data."""
        cache_data.clear()
        cache_timestamp.clear()
        print("System information cache cleared.", type_="INFO")
    
    def get_cpu_info():
        """Get detailed CPU information."""
        try:
            cpu_info = {}
            cpu_info['name'] = platform.processor() or "Unknown Processor"
            cpu_info['architecture'] = platform.architecture()[0]
            cpu_info['cores_physical'] = psutil.cpu_count(logical=False)
            cpu_info['cores_logical'] = psutil.cpu_count(logical=True)
            
            # CPU frequency
            freq = psutil.cpu_freq()
            if freq:
                cpu_info['frequency_current'] = f"{freq.current:.2f} MHz"
                cpu_info['frequency_max'] = f"{freq.max:.2f} MHz" if freq.max else "N/A"
            else:
                cpu_info['frequency_current'] = "N/A"
                cpu_info['frequency_max'] = "N/A"
            
            # CPU usage
            cpu_info['usage_percent'] = psutil.cpu_percent(interval=1)
            cpu_info['usage_per_core'] = psutil.cpu_percent(interval=1, percpu=True)
            
            return cpu_info
        except Exception as e:
            print(f"Error getting CPU info: {e}", type_="ERROR")
            return {"name": "Unknown", "cores_physical": "N/A", "cores_logical": "N/A"}
    
    def get_memory_info():
        """Get detailed memory information."""
        try:
            mem = psutil.virtual_memory()
            swap = psutil.swap_memory()
            
            memory_info = {
                'total': f"{mem.total / (1024**3):.2f} GB",
                'available': f"{mem.available / (1024**3):.2f} GB",
                'used': f"{mem.used / (1024**3):.2f} GB",
                'percentage': f"{mem.percent}%",
                'swap_total': f"{swap.total / (1024**3):.2f} GB" if swap.total > 0 else "No Swap",
                'swap_used': f"{swap.used / (1024**3):.2f} GB" if swap.total > 0 else "N/A",
                'swap_percentage': f"{swap.percent}%" if swap.total > 0 else "N/A"
            }
            return memory_info
        except Exception as e:
            print(f"Error getting memory info: {e}", type_="ERROR")
            return {"total": "N/A", "available": "N/A", "used": "N/A", "percentage": "N/A"}
    
    def get_gpu_info():
        """Get GPU information using various methods."""
        gpu_info = []
        
        # Try wmic on Windows
        try:
            if platform.system() == "Windows":
                result = subprocess.run([
                    'wmic', 'path', 'win32_VideoController', 'get', 
                    'name,AdapterRAM,DriverVersion,VideoProcessor', '/format:csv'
                ], capture_output=True, text=True, timeout=10)
                
                if result.returncode == 0:
                    lines = [line.strip() for line in result.stdout.strip().split('\n') if line.strip()]
                    if len(lines) > 1:  # Skip header
                        for line in lines[1:]:
                            parts = line.split(',')
                            if len(parts) >= 5 and parts[2]:  # Check if name exists
                                vram = "Unknown"
                                if parts[1] and parts[1].isdigit():
                                    vram_bytes = int(parts[1])
                                    if vram_bytes > 0:
                                        vram = f"{vram_bytes / (1024**3):.2f} GB"
                                
                                gpu_info.append({
                                    'name': parts[2],
                                    'vram': vram,
                                    'driver': parts[3] if parts[3] else "N/A"
                                })
        except Exception as e:
            print(f"Error getting GPU info via wmic: {e}", type_="ERROR")
        
        # Fallback: Try lspci on Linux
        if not gpu_info and platform.system() == "Linux":
            try:
                result = subprocess.run(['lspci', '-mm'], capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    for line in result.stdout.split('\n'):
                        if 'VGA' in line or 'Display' in line:
                            parts = line.split('"')
                            if len(parts) >= 6:
                                gpu_info.append({
                                    'name': parts[5],
                                    'vram': "Unknown",
                                    'driver': "N/A"
                                })
            except Exception as e:
                print(f"Error getting GPU info via lspci: {e}", type_="ERROR")
        
        return gpu_info if gpu_info else [{"name": "Unknown GPU", "vram": "N/A", "driver": "N/A"}]
    
    def get_storage_info():
        """Get detailed storage information."""
        try:
            storage_devices = []
            partitions = psutil.disk_partitions()
            
            for partition in partitions:
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    device_info = {
                        'device': partition.device,
                        'mountpoint': partition.mountpoint,
                        'filesystem': partition.fstype,
                        'total': f"{usage.total / (1024**3):.2f} GB",
                        'used': f"{usage.used / (1024**3):.2f} GB",
                        'free': f"{usage.free / (1024**3):.2f} GB",
                        'percentage': f"{(usage.used / usage.total) * 100:.1f}%"
                    }
                    storage_devices.append(device_info)
                except PermissionError:
                    # Skip inaccessible drives
                    continue
                except Exception as e:
                    print(f"Error accessing partition {partition.device}: {e}", type_="ERROR")
                    continue
            
            return storage_devices
        except Exception as e:
            print(f"Error getting storage info: {e}", type_="ERROR")
            return []
    
    def get_network_info():
        """Get network adapter information."""
        try:
            network_info = []
            
            # Get network interfaces
            interfaces = psutil.net_if_addrs()
            stats = psutil.net_if_stats()
            
            for interface_name, addresses in interfaces.items():
                if interface_name in stats:
                    stat = stats[interface_name]
                    if stat.isup:  # Only show active interfaces
                        interface_info = {
                            'name': interface_name,
                            'speed': f"{stat.speed} Mbps" if stat.speed > 0 else "Unknown Speed",
                            'mtu': stat.mtu,
                            'has_connection': len(addresses) > 0
                        }
                        
                        network_info.append(interface_info)
            
            return network_info
        except Exception as e:
            print(f"Error getting network info: {e}", type_="ERROR")
            return []
    
    def get_system_info():
        """Get general system information."""
        try:
            boot_time = datetime.fromtimestamp(psutil.boot_time())
            uptime = datetime.now() - boot_time
            
            system_info = {
                'os_name': f"{platform.system()} {platform.release()}",
                'os_version': platform.version(),
                'hostname': socket.gethostname(),
                'architecture': platform.architecture()[0],
                'boot_time': boot_time.strftime("%Y-%m-%d %H:%M:%S"),
                'uptime': str(uptime).split('.')[0],  # Remove microseconds
                'python_version': platform.python_version()
            }
            
            return system_info
        except Exception as e:
            print(f"Error getting system info: {e}", type_="ERROR")
            return {"os_name": "Unknown", "hostname": "Unknown"}
    
    def get_temperature_info():
        """Get system temperature information if available."""
        try:
            temps = psutil.sensors_temperatures()
            temp_info = {}
            
            for name, entries in temps.items():
                temp_info[name] = []
                for entry in entries:
                    temp_data = {
                        'label': entry.label or 'Unknown',
                        'current': f"{entry.current}°C",
                        'high': f"{entry.high}°C" if entry.high else "N/A",
                        'critical': f"{entry.critical}°C" if entry.critical else "N/A"
                    }
                    temp_info[name].append(temp_data)
            
            return temp_info
        except Exception as e:
            return {}
    
    def format_basic_specs():
        """Format basic system specifications for embed with inline fields."""
        cpu = get_cached_or_fetch('cpu', get_cpu_info)
        memory = get_cached_or_fetch('memory', get_memory_info)
        gpu_list = get_cached_or_fetch('gpu', get_gpu_info)
        storage = get_cached_or_fetch('storage', get_storage_info)
        system = get_cached_or_fetch('system', get_system_info)
        
        # Create fields for inline display
        fields = []
        
        # System Overview Fields
        fields.append({
            "name": "Operating System",
            "value": f"> {system['os_name']}\n> Architecture: {system['architecture']}\n> Hostname: {system['hostname']}",
            "inline": True
        })
        
        fields.append({
            "name": "System Uptime",
            "value": f"> Boot Time: {system['boot_time']}\n> Uptime: {system['uptime']}\n> Python: {system['python_version']}",
            "inline": True
        })
        
        # CPU Fields
        fields.append({
            "name": "Processor",
            "value": f"> {cpu['name']}\n> Cores: {cpu['cores_physical']} physical, {cpu['cores_logical']} logical\n> Usage: {cpu['usage_percent']}%",
            "inline": True
        })
        
        fields.append({
            "name": "CPU Frequency",
            "value": f"> Current: {cpu['frequency_current']}\n> Maximum: {cpu['frequency_max']}",
            "inline": True
        })
        
        # Memory Fields
        fields.append({
            "name": "Memory Usage",
            "value": f"> Total: {memory['total']}\n> Used: {memory['used']} ({memory['percentage']})\n> Available: {memory['available']}",
            "inline": True
        })
        
        if memory['swap_total'] != "No Swap":
            fields.append({
                "name": "Swap Memory",
                "value": f"> Total: {memory['swap_total']}\n> Used: {memory['swap_used']} ({memory['swap_percentage']})",
                "inline": True
            })
        
        # GPU Fields
        for i, gpu in enumerate(gpu_list):
            fields.append({
                "name": f"Graphics Card {i+1}" if len(gpu_list) > 1 else "Graphics Card",
                "value": f"> {gpu['name']}\n> VRAM: {gpu['vram']}\n> Driver: {gpu['driver']}",
                "inline": True
            })
        
        # Storage Fields
        for i, drive in enumerate(storage[:3]):  # Limit to 3 drives for space
            fields.append({
                "name": f"Storage {drive['device']}",
                "value": f"> Filesystem: {drive['filesystem']}\n> Size: {drive['total']}\n> Used: {drive['used']} ({drive['percentage']})\n> Free: {drive['free']}",
                "inline": True
            })
        
        return fields
    
    def format_detailed_specs():
        """Format detailed system specifications including performance metrics."""
        basic_fields = format_basic_specs()
        network = get_cached_or_fetch('network', get_network_info)
        temps = get_cached_or_fetch('temperatures', get_temperature_info)
        cpu = get_cached_or_fetch('cpu', get_cpu_info)
        
        # Add per-core CPU usage
        cpu_cores_text = ""
        cores_per_line = 4
        for i in range(0, len(cpu['usage_per_core']), cores_per_line):
            line_cores = cpu['usage_per_core'][i:i+cores_per_line]
            line_text = " | ".join([f"Core {j+i+1}: {usage}%" for j, usage in enumerate(line_cores)])
            cpu_cores_text += f"> {line_text}\n"
        cpu_cores_text = cpu_cores_text.rstrip()
        
        basic_fields.append({
            "name": "CPU Core Usage",
            "value": cpu_cores_text,
            "inline": False
        })
        
        # Network Information
        if network:
            for interface in network[:2]:  # Limit to 2 interfaces
                connection_status = "Connected" if interface['has_connection'] else "No Connection"
                
                basic_fields.append({
                    "name": f"Network {interface['name']}",
                    "value": f"> Speed: {interface['speed']}\n> MTU: {interface['mtu']}\n> Status: {connection_status}",
                    "inline": True
                })
        
        # Temperature Information
        if temps:
            temp_text = ""
            temp_count = 0
            for sensor_name, entries in temps.items():
                if temp_count >= 6:  # Limit temperature sensors
                    break
                for entry in entries:
                    if temp_count >= 6:
                        break
                    temp_text += f"> {entry['label']}: {entry['current']}"
                    if entry['high'] != "N/A":
                        temp_text += f" (High: {entry['high']})"
                    temp_text += "\n"
                    temp_count += 1
            
            if temp_text:
                basic_fields.append({
                    "name": "System Temperatures",
                    "value": temp_text.rstrip(),
                    "inline": True
                })
        
        return basic_fields
    
    def export_to_json(detailed=False):
        """Export system information to JSON file."""
        try:
            export_data = {
                'export_time': datetime.now().isoformat(),
                'system': get_cached_or_fetch('system', get_system_info),
                'cpu': get_cached_or_fetch('cpu', get_cpu_info),
                'memory': get_cached_or_fetch('memory', get_memory_info),
                'gpu': get_cached_or_fetch('gpu', get_gpu_info),
                'storage': get_cached_or_fetch('storage', get_storage_info)
            }
            
            if detailed:
                export_data['network'] = get_cached_or_fetch('network', get_network_info)
                export_data['temperatures'] = get_cached_or_fetch('temperatures', get_temperature_info)
            
            # Save to JSON file
            json_dir = Path(getScriptsPath()) / "json"
            json_dir.mkdir(parents=True, exist_ok=True)
            
            filename = f"system_specs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            filepath = json_dir / filename
            
            with open(filepath, 'w') as f:
                json.dump(export_data, f, indent=4, default=str)
            
            print(f"System specifications exported to {filepath}", type_="SUCCESS")
            return str(filepath)
        except Exception as e:
            print(f"Error exporting system specs: {e}", type_="ERROR")
            return None
    
    @bot.command(
        name="sysinfo",
        aliases=["specs", "hwinfo"],
        usage="[--detailed] [--export] [--refresh]",
        description="Display comprehensive system specifications and hardware information"
    )
    async def system_info_command(ctx, *, args: str = ""):
        await ctx.message.delete()
        
        # Parse arguments
        detailed = "--detailed" in args
        export = "--export" in args
        refresh = "--refresh" in args
        
        if refresh:
            clear_cache()
        
        try:
            # Disable private mode temporarily for embed sending
            current_private = getConfigData().get("private")
            updateConfigData("private", False)
            
            # Show status message for longer operations
            status_msg = await ctx.send("Gathering system information...")
            
            # Get system specifications
            if detailed:
                fields = format_detailed_specs()
                title = "Advanced System Specifications"
            else:
                fields = format_basic_specs()
                title = "System Specifications"
            
            # Export if requested
            export_path = None
            if export:
                await status_msg.edit(content="Exporting system information...")
                export_path = export_to_json(detailed)
            
            # Get system info for description
            system = get_cached_or_fetch('system', get_system_info)
            description = f"> Hostname: {system['hostname']}\n> Operating System: {system['os_name']}\n> Architecture: {system['architecture']}\n> System Uptime: {system['uptime']}"
            
            # Create a single formatted description with all the information
            full_description = description + "\n\n"
            
            # Add all field information to the description
            for field in fields:
                full_description += f"{field['name']}:\n{field['value']}\n\n"
            
            # Send the main embed
            await forwardEmbedMethod(
                channel_id=ctx.channel.id,
                content=full_description.rstrip(),
                title=title
            )
            
            # Show export confirmation if requested
            if export_path:
                await forwardEmbedMethod(
                    channel_id=ctx.channel.id,
                    content=f"> System specifications exported to:\n> {export_path}",
                    title="Export Complete"
                )
            
            # Delete status message
            await status_msg.delete()
            
        except Exception as e:
            print(f"Error in sysinfo command: {e}", type_="ERROR")
            await ctx.send(f"Error: Failed to retrieve system information: {str(e)}")
        finally:
            # Restore original private setting
            updateConfigData("private", current_private)
    
    @bot.command(
        name="clearcache",
        description="Clear the system information cache to force refresh"
    )
    async def clear_cache_command(ctx, *, args: str = ""):
        await ctx.message.delete()
        clear_cache()
        await ctx.send("System information cache cleared.", delete_after=3)

# Initialize the script
script_function()
