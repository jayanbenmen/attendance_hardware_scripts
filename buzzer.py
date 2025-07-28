import lgpio
import time

# GPIO setup
buzzer_pin = 18

# Open GPIO chip 
chip = lgpio.gpiochip_open(0)

try:
    try:
        lgpio.gpio_free(chip, buzzer_pin)
    except lgpio.error as e:
        if "GPIO not allocated" not in str(e):
            raise

    # Set pin as output
    lgpio.gpio_claim_output(chip, buzzer_pin)

    # Function for beep
    def beep(frequency, duration):
        try:
            period = 1.0 / frequency 
            end_time = time.time() + duration


            while time.time() < end_time:
                lgpio.gpio_write(chip, buzzer_pin, 1)  
                time.sleep(period / 2)                 
                lgpio.gpio_write(chip, buzzer_pin, 0)  
                time.sleep(period / 2)                 

        except Exception as e:
            print(f"Error during beep: {e}")
        
        finally:
            lgpio.gpio_free(chip, buzzer_pin)

except Exception as e:
    print(f"GPIO setup error: {e}")

finally:
    lgpio.gpiochip_close(chip)

