import unittest

from commands import *


class TestValidateContractInput(unittest.TestCase):
    def test_valid_input(self):
        errors = validate_contract(Contract('1234', 'Juhdu', 'Khigbaa', 5000))
        self.assertEqual(len(errors), 0)


    def assert_error(self, errors, field, message):
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].field, field)
        self.assertEqual(errors[0].message, message)


    def test_invalid_seals(self):
        tests = [0, -1, -100]
        for test in tests:
            with self.subTest(amount=test):
                errors = validate_contract(Contract('1234', 'Juhdu', 'Khigbaa', test))
                self.assert_error(errors, 'amount', 'Amount must be a positive integer.')

    
    def test_invalid_first_name(self):
        tests = ['', 'Juhdu with Spaces', 'Juhdu-Khigbaa', ' ', '/4iieh)OEWP\\']
        for test in tests:
            with self.subTest(first_name=test):
                errors = validate_contract(Contract('1234', test, 'Khigbaa', 5000))
                self.assert_error(errors, 'first_name', 'First name must be non-empty and alphabetic.')

        
    def test_invalid_last_name(self):
        tests = ['', 'Khigbaa with Spaces', 'Khigbaa-Khigbaa', ' ', '/4iieh)OEWP\\']
        for test in tests:
            with self.subTest(last_name=test):
                errors = validate_contract(Contract('1234', 'Juhdu', test, 5000))
                self.assert_error(errors, 'last_name', 'Last name must be non-empty and alphabetic.')


class TestCreateContract(unittest.IsolatedAsyncioTestCase):
    async def test_happy_path(self):
        contract = Contract(
            discord_id='123456789012345678',
            first_name='Juhdu',
            last_name='Khigbaa',
            amount=5000
        )
        await create_contract(contract)


    async def test_invalid_contract_raises_exception(self):
        contract = Contract(
            discord_id='123456789012345678',
            first_name='Juhdu 123',
            last_name='Khigba  a',
            amount=-5000
        )
        with self.assertRaises(ValidationException) as ve:
            await create_contract(contract)
        errors = ve.exception.errors
        self.assertEqual(errors, [
            ValidationError('first_name', 'First name must be non-empty and alphabetic.'),
            ValidationError('last_name', 'Last name must be non-empty and alphabetic.'),
            ValidationError('amount', 'Amount must be a positive integer.')
        ])
