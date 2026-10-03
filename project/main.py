"""
Okey Bot - Main Entry Point
Orchestrates card recognition, decision making, and game automation
"""

from card_recognizer import CardRecognizer
from decision_engine import DecisionEngine
from game_automation import GameAutomation
from config import TIMINGS, DEBUG
import time


class OkeyBot:
    """Main bot that orchestrates all components"""
    
    def __init__(self):
        """Initialize all bot components"""
        print("=" * 50)
        print("OKEY BOT - Initializing...")
        print("=" * 50)
        
        self.recognizer = CardRecognizer()
        self.decision_engine = DecisionEngine()
        self.automator = GameAutomation()
        
        self.iteration = 0
        self.running = False
        
        print("\n✓ All components initialized!")
        print("\nInstructions:")
        print("  1. Focus the game window")
        print("  2. Press ENTER to start the bot")
        print("  3. Move mouse to TOP-LEFT CORNER to emergency stop")
        print("=" * 50)
    
    def run(self):
        """Main bot loop - recognizes cards, makes decisions, executes actions"""
        self.running = True
        
        print("\n🤖 Bot is running... (move mouse to corner to stop)\n")
        
        while self.running:
            self.iteration += 1
            
            try:
                # ========== STEP 1: READ CARDS ==========
                if DEBUG:
                    print(f"\n{'='*50}")
                    print(f"ITERATION {self.iteration}")
                    print(f"{'='*50}")
                
                print(f"\n[{self.iteration}] Reading cards...")
                cards = self.recognizer.read_cards()
                
                if not cards:
                    print("  ⚠ No cards detected. Waiting...")
                    self.automator.wait(TIMINGS["loop_delay"])
                    continue
                
                # Display detected cards
                print(f"  ✓ Detected {len(cards)} cards:")
                for card in cards:
                    print(f"    • {card['color']:6s} {card['number']}")
                
                # ========== STEP 2: MAKE DECISION ==========
                print(f"\n[{self.iteration}] Making decision...")
                decision = self.decision_engine.decide(cards)
                
                # Display decision
                print(f"  ✓ Decision: {decision['action'].upper()}")
                print(f"    Reason: {decision['reason']}")
                
                # ========== STEP 3: EXECUTE DECISION ==========
                print(f"\n[{self.iteration}] Executing action...")
                self.automator.execute_decision(cards, decision)
                print(f"  ✓ Action completed")
                
                # ========== STEP 4: WAIT FOR GAME ==========
                print(f"\n[{self.iteration}] Waiting for game to respond...")
                self.automator.wait(TIMINGS["loop_delay"])
                
            except KeyboardInterrupt:
                print("\n\n❌ Bot stopped by user (Ctrl+C)")
                self.running = False
                break
            
            except Exception as e:
                print(f"\n⚠ Error occurred: {e}")
                if DEBUG:
                    import traceback
                    traceback.print_exc()
                
                print("  Waiting before retry...")
                self.automator.wait(TIMINGS["loop_delay"])
        
        print("\n" + "=" * 50)
        print("Bot shutdown complete")
        print("=" * 50)
    
    def test_card_recognition(self):
        """Test mode: just read cards without playing"""
        print("\n🧪 TEST MODE - Card Recognition Only")
        print("=" * 50)
        
        try:
            for i in range(5):
                print(f"\nTest {i+1}/5:")
                cards = self.recognizer.read_cards()
                
                if cards:
                    print(f"✓ Detected {len(cards)} cards:")
                    for card in cards:
                        print(f"  • {card['color']:6s} {card['number']}")
                else:
                    print("⚠ No cards detected")
                
                if i < 4:
                    time.sleep(2)
        
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()


def main():
    """Entry point"""
    bot = OkeyBot()
    
    # Uncomment ONE of the following:
    
    # Option 1: Run full bot
    bot.run()
    
    # Option 2: Test card recognition only (uncomment to use)
    # bot.test_card_recognition()


if __name__ == "__main__":
    main()
