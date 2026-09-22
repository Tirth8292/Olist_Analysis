DROP TABLE IF EXISTS product_review;
CREATE TABLE product_review AS
SELECT r.review_id, r.order_id, r.review_score,
       r.review_comment_title, r.review_comment_message,
       r.review_creation_date, r.review_answer_timestamp,
       i.product_id, t.product_category_name_english
FROM order_reviews AS r
LEFT JOIN order_items AS i ON r.order_id = i.order_id
LEFT JOIN products AS p ON i.product_id = p.product_id
LEFT JOIN category_translation AS t ON p.product_category_name = t.product_category_name;
