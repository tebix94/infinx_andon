from pydantic import BaseModel, Field, model_validator

class UserCreateSchema(BaseModel):
    employee_number: str = Field(min_length=4, max_length=10)
    employee_number_admin: str = Field(min_length=4, max_length=10)
    #password: str = Field(min_length=8)
    #password_confirmation: str
    first_name: str
    last_name: str
    role_name: str

    # This is the "Magic" that replaces your manual IF checks
    '''
    @model_validator(mode='after')
    def check_passwords_match(self) -> 'UserCreateSchema':
        pw1 = self.password
        pw2 = self.password_confirmation
        if pw1 is not None and pw2 is not None and pw1 != pw2:
            raise ValueError('passwords do not match')
        return self
    ''' 
'''
class UserLoginSchema(BaseModel):
    employee_id: str = Field(min_length=3, max_length=20)
    #password: str = Field(min_length=8)
'''

class CreatePostSchema(BaseModel):
    employee_number: str = Field(min_length=4, max_length=10)
    machine_id: str
    interruption_id: str
    description: str