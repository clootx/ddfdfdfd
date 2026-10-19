// This endpoint is used to validate that sendgrid is working.
query "sendgrid/validate" verb=POST {
  api_group = "Sendgrid Validation"

  input {
    email to_email?
    text subject? filters=trim
    text body? filters=trim
  }

  stack {
    function.run sendgrid_basic_send {
      input = {
        to_email: $input.to_email
        subject : $input.subject
        body    : $input.body
      }
    } as $func_1
  }

  response = {status: "success"}
  guid = "tSSPmFXre3-MQ55biKk27v4NBxg"
}