# Payment card declined

Evidence required: payment decline log, provider response code, and matching
trace. Treat a hard decline as a business outcome unless its rate rises above
the expected baseline; do not blindly retry the transaction.
