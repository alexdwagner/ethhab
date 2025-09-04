from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

Base = declarative_base()

class Whale(Base):
    __tablename__ = 'whales'
    
    id = Column(Integer, primary_key=True)
    address = Column(String(42), unique=True, nullable=False)
    first_seen = Column(DateTime, default=datetime.utcnow)
    current_balance = Column(Float, nullable=False)
    max_balance = Column(Float, nullable=False)
    total_volume = Column(Float, default=0.0)
    transaction_count = Column(Integer, default=0)
    last_activity = Column(DateTime)
    whale_tier = Column(String(20))  # mini, large, mega, institutional
    is_active = Column(Boolean, default=True)
    notes = Column(Text)

class Transaction(Base):
    __tablename__ = 'transactions'
    
    id = Column(Integer, primary_key=True)
    hash = Column(String(66), unique=True, nullable=False)
    whale_address = Column(String(42), nullable=False)
    from_address = Column(String(42), nullable=False)
    to_address = Column(String(42), nullable=False)
    amount = Column(Float, nullable=False)
    gas_price = Column(Float)
    gas_used = Column(Integer)
    block_number = Column(Integer, nullable=False)
    timestamp = Column(DateTime, nullable=False)
    transaction_type = Column(String(20))  # inflow, outflow, internal

class Alert(Base):
    __tablename__ = 'alerts'
    
    id = Column(Integer, primary_key=True)
    whale_address = Column(String(42), nullable=False)
    alert_type = Column(String(50), nullable=False)  # large_transaction, accumulation, distribution
    message = Column(Text, nullable=False)
    amount = Column(Float)
    timestamp = Column(DateTime, default=datetime.utcnow)
    is_read = Column(Boolean, default=False)

class DatabaseManager:
    def __init__(self):
        database_url = os.getenv('DATABASE_URL', 'sqlite:///whale_tracker.db')
        self.engine = create_engine(database_url)
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
    
    def add_whale(self, address, balance):
        """Add a new whale to tracking"""
        existing = self.session.query(Whale).filter_by(address=address).first()
        if existing:
            return existing
        
        # Determine whale tier
        if balance >= 100000:
            tier = "institutional"
        elif balance >= 10000:
            tier = "mega"
        elif balance >= 1000:
            tier = "large"
        else:
            tier = "mini"
        
        whale = Whale(
            address=address,
            current_balance=balance,
            max_balance=balance,
            whale_tier=tier
        )
        self.session.add(whale)
        self.session.commit()
        return whale
    
    def update_whale_balance(self, address, new_balance):
        """Update whale balance and check for tier changes"""
        whale = self.session.query(Whale).filter_by(address=address).first()
        if whale:
            whale.current_balance = new_balance
            if new_balance > whale.max_balance:
                whale.max_balance = new_balance
            
            # Update tier if needed
            if new_balance >= 100000:
                whale.whale_tier = "institutional"
            elif new_balance >= 10000:
                whale.whale_tier = "mega"
            elif new_balance >= 1000:
                whale.whale_tier = "large"
            else:
                whale.whale_tier = "mini"
            
            self.session.commit()
    
    def add_transaction(self, tx_data):
        """Add a transaction to the database"""
        existing = self.session.query(Transaction).filter_by(hash=tx_data['hash']).first()
        if existing:
            return existing
        
        transaction = Transaction(**tx_data)
        self.session.add(transaction)
        self.session.commit()
        return transaction
    
    def add_alert(self, whale_address, alert_type, message, amount=None):
        """Add an alert for whale activity"""
        alert = Alert(
            whale_address=whale_address,
            alert_type=alert_type,
            message=message,
            amount=amount
        )
        self.session.add(alert)
        self.session.commit()
        return alert
    
    def get_top_whales(self, limit=100):
        """Get top whales by current balance"""
        return self.session.query(Whale)\
            .filter(Whale.is_active == True)\
            .order_by(Whale.current_balance.desc())\
            .limit(limit).all()
    
    def get_recent_alerts(self, limit=50):
        """Get recent alerts"""
        return self.session.query(Alert)\
            .order_by(Alert.timestamp.desc())\
            .limit(limit).all()
    
    def close(self):
        """Close database connection"""
        self.session.close()